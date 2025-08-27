import discord
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
import os
from dotenv import load_dotenv

# --- CARREGAR VARIÁVEIS DE AMBIENTE ---
load_dotenv()

# --- CONFIGURAÇÃO INICIAL ---
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID_STR = os.getenv("GUILD_ID")

if not TOKEN or not GUILD_ID_STR:
    print("Erro: 'DISCORD_TOKEN' ou 'GUILD_ID' não foram encontrados no arquivo .env")
    exit()

GUILD_ID = discord.Object(id=int(GUILD_ID_STR))

# Dicionário para armazenar os IDs dos canais
# Agora armazena o canal de reviews e o canal do painel
server_configs = {}

# --- EMOJIS CUSTOMIZADOS ---
WHITE_ARROW = "<a:white_arrow:1327361152530911333>"
CORACAO_ANIMADO = "<:coracaoanimado:1336397477489938433>"
MEMBROS = "<:membros:1336397481184989235>"
VERIFICADO_ROXO = "<:verificadoroxo:1336397483542188073>"
DIAMANTE_ROXO = "<:diamanteroxo:1336397479612121119>"
ESTRELA = "<:estrela:1336393802319138846>"

# --- BOT ---
class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=GUILD_ID)
        await self.tree.sync(guild=GUILD_ID)

    async def on_ready(self):
        print(f'Logado como {self.user} (ID: {self.user.id})')
        print('------')
        self.add_view(AvaliacaoView())

intents = discord.Intents.default()
client = MyClient(intents=intents)

# --- MODAL DE AVALIAÇÃO ---
class AvaliacaoModal(Modal, title='Deixe sua Avaliação'):
    # Esta classe não precisa de grandes mudanças
    def __init__(self, review_channel_id: int):
        super().__init__()
        self.review_channel_id = review_channel_id

    nota = TextInput(
        label='Nota (de 1 a 5)',
        placeholder='Ex: 5',
        required=True, min_length=1, max_length=1
    )

    avaliacao_texto = TextInput(
        label='Sua avaliação',
        style=discord.TextStyle.paragraph,
        placeholder='Descreva sua experiência com o atendimento e o serviço.',
        required=True, min_length=10, max_length=1024
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            nota_int = int(self.nota.value)
            if not 1 <= nota_int <= 5:
                await interaction.response.send_message("Por favor, insira uma nota válida de 1 a 5.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("O valor da nota deve ser um número.", ephemeral=True)
            return
        
        # O ID do canal de feedbacks já é recebido corretamente
        review_channel = interaction.guild.get_channel(self.review_channel_id)
        if not review_channel:
            await interaction.response.send_message("O canal de feedbacks não foi encontrado. Contate um administrador.", ephemeral=True)
            return

        embed = discord.Embed(color=discord.Color.from_rgb(71, 199, 100))
        embed.description = (
            f"{CORACAO_ANIMADO} | **Nova avaliação**\n\n"
            f"{MEMBROS} | **Avaliação enviada por:**\n{interaction.user.mention}\n\n"
            f"{VERIFICADO_ROXO} | **Nota: ({nota_int}/5)**\n{''.join([ESTRELA for _ in range(nota_int)])}\n\n"
            f"{DIAMANTE_ROXO} | **Avaliação:**\n{self.avaliacao_texto.value}"
        )

        try:
            await review_channel.send(embed=embed)
            await interaction.response.send_message('Sua avaliação foi enviada com sucesso! Obrigado.', ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message('Não tenho permissão para enviar mensagens no canal de feedbacks. Avise um administrador.', ephemeral=True)
        except Exception as e:
            print(f"Erro ao enviar avaliação: {e}")
            await interaction.response.send_message('Ocorreu um erro ao enviar sua avaliação.', ephemeral=True)


# --- VIEW COM O BOTÃO "AVALIAR" ---
class AvaliacaoView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Avaliar', style=discord.ButtonStyle.green, emoji='⭐', custom_id='avaliar_button_persistente')
    async def avaliar_button(self, interaction: discord.Interaction, button: Button):
        guild_id = interaction.guild.id
        # Verifica se a configuração existe
        if guild_id not in server_configs or 'review_channel' not in server_configs[guild_id]:
            await interaction.response.send_message(
                "O sistema de avaliações não foi configurado. Peça para um admin usar `/setup`.",
                ephemeral=True
            )
            return
        
        # Pega o ID do canal de feedbacks e passa para o Modal
        review_channel_id = server_configs[guild_id]['review_channel']
        await interaction.response.send_modal(AvaliacaoModal(review_channel_id=review_channel_id))


# --- COMANDO DE SETUP (MODIFICADO) ---
@client.tree.command(name="setup", description="Configura os canais de avaliação.")
# MUDANÇA 1: Adicionados dois parâmetros de canal com descrições claras
@app_commands.describe(
    canal_painel="O canal onde o painel para clicar e avaliar ficará.",
    canal_feedbacks="O canal onde as avaliações prontas serão enviadas."
)
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, canal_painel: discord.TextChannel, canal_feedbacks: discord.TextChannel):
    # MUDANÇA 2: Armazena os dois IDs de canais
    server_configs[interaction.guild.id] = {
        'setup_channel': canal_painel.id,
        'review_channel': canal_feedbacks.id
    }

    embed = discord.Embed(
        title="⭐ Painel Avaliações",
        description=(
            f"{WHITE_ARROW} **Clique no botão abaixo!**\n\n"
            "**Sistema de avaliações do servidor.**\n\n"
            "**Faça já sua avaliação do nosso atendimento.**"
        ),
        color=discord.Color.from_rgb(71, 199, 100)
        )
    embed.set_author(name="Litz 8 Ball Pool Store")
    embed.set_thumbnail(url="https://imgur.com/tzNQI3q.png")

    try:
        # MUDANÇA 3: Envia o painel para o canal_painel especificado
        await canal_painel.send(embed=embed, view=AvaliacaoView())
        
        # MUDANÇA 4: Mensagem de sucesso informa os dois canais configurados
        await interaction.response.send_message(
            f"✅ Sucesso! O painel de avaliações foi enviado para {canal_painel.mention} "
            f"e os feedbacks serão postados em {canal_feedbacks.mention}.",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message("❌ Não tenho permissão para enviar mensagens em um dos canais. Verifique minhas permissões.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Ocorreu um erro: {e}", ephemeral=True)

@setup.error
async def setup_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Você não tem permissão de administrador para usar este comando.", ephemeral=True)

# --- EXECUÇÃO DO BOT ---
client.run(TOKEN)