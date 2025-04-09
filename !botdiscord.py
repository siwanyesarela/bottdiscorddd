import os
import discord
import aiohttp
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Load token dari file .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN is None:
    print("ERROR: Token tidak ditemukan! Pastikan file .env sudah benar.")
    exit()

# URL API FiveM & Logo Server
FIVEM_SERVERS = {
    "ni": {
        "url": "https://servers-frontend.fivem.net/api/servers/single/88x6zb",
        "logo": "https://media.discordapp.net/attachments/1218529915721351278/1346045483704909845/NusaIndah_FinalLogo.png"
    },
    "kb": {
        "url": "https://servers-frontend.fivem.net/api/servers/single/mez5p7",
        "logo": "https://media.discordapp.net/attachments/951083994370433055/1248594024881848332/KB-h_1.png"
    },
    "idp": {
        "url": "https://servers-frontend.fivem.net/api/servers/single/237yxy",
        "logo": "https://cdn.discordapp.com/attachments/616666479940599811/1022545370456268891/logo_indopride_v2-01.png"
    },
    "hope": {
        "url": "https://servers-frontend.fivem.net/api/servers/single/brm6gd",
        "logo": "https://cdn.discordapp.com/attachments/929186470919565313/1140947550132772904/3.png"
    },
    "jing": {
        "url": "https://servers-frontend.fivem.net/api/servers/single/53k9ra",
        "logo": "https://cdn.discordapp.com/attachments/1183700333797589022/1328681412106387509/JING-ARENA-500_1.webp"
    },
}

# Hanya izinkan perintah di channel tertentu
WHITELISTED_CHANNELS = {1200016475700854824, 1351896577341522001, 1351599217478471754, 1358058349500825732}

# Intents
intents = discord.Intents.default()
intents.message_content = True

# Inisialisasi bot
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot {bot.user} siap digunakan!")

def is_allowed_channel(ctx):
    return ctx.channel.id in WHITELISTED_CHANNELS

# Fungsi ambil data pemain dari API FiveM
async def fetch_players(server_name):
    if server_name not in FIVEM_SERVERS:
        return None
    url = FIVEM_SERVERS[server_name]["url"]
    timeout = aiohttp.ClientTimeout(total=15)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("Data", {}).get("players", [])
                return None
    except (asyncio.TimeoutError, aiohttp.ClientError):
        return "TIMEOUT"

# Fungsi pembagi halaman
def split_players(players, chunk_size=20):
    return [players[i:i + chunk_size] for i in range(0, len(players), chunk_size)]

# Perintah !cek
@bot.command()
async def cek(ctx, server_name: str, *, query: str = None):
    if not is_allowed_channel(ctx):
        return await ctx.send("Perintah ini hanya bisa digunakan di channel tertentu.")

    if server_name not in FIVEM_SERVERS:
        return await ctx.send(f"Server `{server_name}` tidak ditemukan.")

    players = await fetch_players(server_name)

    if players == "TIMEOUT":
        return await ctx.send(f"Gagal mengakses server `{server_name}` (timeout).")

    if players is None:
        return await ctx.send(f"Terjadi kesalahan saat mengambil data dari server `{server_name}`.")

    if query:
        players = [p for p in players if query.lower() in str(p.get("id", "")) 
                                      or query.lower() in p.get("name", "").lower()
                                      or query.lower() in str(p.get("ping", ""))]
        if not players:
            embed = discord.Embed(
                title="Pemain Tidak Ditemukan",
                description=f"Tidak ada pemain dengan nama `{query}` di server `{server_name}`.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

    if not players:
        return await ctx.send(f"Tidak ada pemain online di server `{server_name}`.")

    pages = split_players(players)
    total_pages = len(pages)

    async def build_embed(page_idx):
        embed = discord.Embed(
            title=f"{server_name.upper()} - {len(players)} Pemain Online",
            description=f"Page {page_idx+1}/{total_pages}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=FIVEM_SERVERS[server_name]["logo"])
        content = "\n".join([f"({p.get('id', '?')}) {p.get('name', 'Unknown')[:40]}" for p in pages[page_idx]])
        embed.add_field(name="Daftar Pemain:", value=f"```{content}```", inline=False)
        return embed

    message = await ctx.send(embed=await build_embed(0))

    if total_pages > 1:
        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id

        current_page = 0
        while True:
            try:
                reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=check)
                if reaction.emoji == "➡️" and current_page < total_pages - 1:
                    current_page += 1
                elif reaction.emoji == "⬅️" and current_page > 0:
                    current_page -= 1
                await message.edit(embed=await build_embed(current_page))
                await message.remove_reaction(reaction.emoji, ctx.author)
            except asyncio.TimeoutError:
                break

# Jalankan bot
try:
    bot.run(TOKEN)
except discord.LoginFailure:
    print("Token tidak valid. Cek kembali file .env kamu.")
