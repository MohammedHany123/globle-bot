import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
from game import GlobleGame
from map_generator import MapGenerator

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Store active games per channel
active_games = {}

# Map generator instance (initialized once at startup)
map_generator = None


async def _generate_and_send_map(channel_id: int, game: GlobleGame, guess_count: int):
    """Generate the PNG map in a thread and send it to the channel, then cleanup."""
    if not map_generator:
        return

    try:
        # Run blocking generation in a thread
        guesses = game.get_guesses_for_map()
        png_path = await asyncio.to_thread(map_generator.generate_guess_map, guesses, game.target_country, guess_count)

        # Find channel (cached or fetch)
        channel = bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(channel_id)
            except Exception:
                return

        discord_file = discord.File(png_path, filename='globle_map.png')
        embed = discord.Embed(
            title=f"🗺️ Map - Guess #{guess_count}",
            description=f"Total guesses: {game.guess_count}\nPlayers: {', '.join(game.players)}",
            color=discord.Color.blue()
        )
        embed.set_image(url='attachment://globle_map.png')

        await channel.send(file=discord_file, embed=embed)
    except Exception as e:
        print(f"Background map generation error: {e}")
    finally:
        try:
            if 'png_path' in locals() and png_path and os.path.exists(png_path):
                os.remove(png_path)
        except Exception:
            pass

@bot.event
async def on_ready():
    global map_generator
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    print('Loading world map for fast visualization...')
    map_generator = MapGenerator()
    print('Map generator ready! ✅')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

@bot.tree.command(name='start', description='Start a new Globle game')
async def start_game(interaction: discord.Interaction):
    """Start a new geography guessing game"""
    channel_id = interaction.channel.id
    
    if channel_id in active_games:
        await ctx.send("⚠️ A game is already in progress! Use /surrender to end it first.")
        return
    
    # Create new game
    game = GlobleGame()
    active_games[channel_id] = game
    
    embed = discord.Embed(
        title="🌍 Globle Game Started!",
        description="I'm thinking of a country. Try to guess it!\n\n"
                    "**How to play:**\n"
                    "• Use `/guess [country]` to make a guess\n"
                    "• I'll tell you if you're getting HOTTER (closer) or COLDER (farther)\n"
                    "• Distance is measured from capital to capital\n"
                    "• Use `/hint` for a clue\n"
                    "• Use `/surrender` to give up\n\n"
                    "Good luck! 🎯",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='guess', description='Make a guess for the current game')
async def make_guess(interaction: discord.Interaction, country: str):
    """Make a guess for the current game"""
    channel_id = interaction.channel.id
    
    if channel_id not in active_games:
        await interaction.response.send_message("❌ No active game! Use `/start` to begin a new game.")
        return
    
    game = active_games[channel_id]
    result = game.make_guess(country, interaction.user.name)
    
    if result['status'] == 'invalid':
        await interaction.response.send_message(f"❌ '{country}' is not a valid country name. Try again!")
        return
    
    if result['status'] == 'duplicate':
        await interaction.response.send_message(f"🔄 '{country}' has already been guessed!")
        return
    if result['status'] == 'won':
        embed = discord.Embed(
            title="🎉 CONGRATULATIONS! 🎉",
            description=f"**{interaction.user.name}** guessed it!\n\n"
                        f"The country was: **{result['country']}** 🎯\n"
                        f"Total guesses: **{result['guess_count']}**\n"
                        f"Guessed by: {', '.join(result['players'])}\n\n"
                        f"Use `/map` to see the final map!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        del active_games[channel_id]
        return
    
    # Show feedback with hot/cold
    distance_km = result['distance']
    feedback = result['feedback']
    trend = result['trend']
    
    # Color based on distance
    if distance_km < 500:
        color = discord.Color.red()  # Very hot
        emoji = "🔥🔥🔥"
    elif distance_km < 1000:
        color = discord.Color.orange()  # Hot
        emoji = "🔥🔥"
    elif distance_km < 2500:
        color = discord.Color.gold()  # Warm
        emoji = "🔥"
    elif distance_km < 5000:
        color = discord.Color.blue()  # Cool
        emoji = "❄️"
    else:
        color = discord.Color.dark_blue()  # Cold
        emoji = "❄️❄️"
    
    trend_text = ""
    if trend == "hotter":
        trend_text = "🔥 Getting HOTTER!"
    elif trend == "colder":
        trend_text = "❄️ Getting COLDER!"
    elif trend == "same":
        trend_text = "↔️ About the same distance"
    
    embed = discord.Embed(
        title=f"{emoji} {result['country']}",
        description=f"**Distance:** {distance_km:,.0f} km\n"
                    f"**Temperature:** {feedback}\n"
                    f"{trend_text}\n\n"
                    f"Guess #{result['guess_count']}\n\n"
                    f"A map will be posted shortly (if enabled).",
        color=color
    )

    # Send quick feedback immediately
    await interaction.response.send_message(embed=embed)

    # Spawn background task to generate and send the map (non-blocking)
    if map_generator:
        try:
            asyncio.create_task(_generate_and_send_map(channel_id, game, result['guess_count']))
        except Exception as e:
            print(f"Failed to spawn background map task: {e}")

@bot.tree.command(name='hint', description='Get a hint about the target country')
async def get_hint(interaction: discord.Interaction):
    """Get a hint for the current game"""
    channel_id = interaction.channel.id
    
    if channel_id not in active_games:
        await interaction.response.send_message("❌ No active game! Use `/start` to begin a new game.")
        return
    
    game = active_games[channel_id]
    hint = game.get_hint()
    
    embed = discord.Embed(
        title="💡 Hint",
        description=hint,
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='map', description='Show the current game map with your guesses')
async def show_map(interaction: discord.Interaction):
    """Generate and display the current game map"""
    # Defer immediately since map generation takes time
    await interaction.response.defer()
    
    channel_id = interaction.channel.id
    
    if channel_id not in active_games:
        await interaction.followup.send("❌ No active game! Use `/start` to begin a new game.")
        return
    
    if not map_generator:
        await interaction.followup.send("❌ Map generator is not available. Missing required libraries.")
        return
    
    game = active_games[channel_id]
    
    if game.guess_count == 0:
        await interaction.followup.send("❌ Make at least one guess first!")
        return
    
    try:
        guesses = game.get_guesses_for_map()
        png_path = map_generator.generate_guess_map(guesses, game.target_country, game.guess_count)
        
        discord_file = discord.File(png_path, filename='globle_map.png')
        
        embed = discord.Embed(
            title=f"🗺️ Current Game Map - Guess #{game.guess_count}",
            description=f"Total guesses: {game.guess_count}\n"
                        f"Players: {', '.join(game.players)}",
            color=discord.Color.blue()
        )
        embed.set_image(url='attachment://globle_map.png')
        
        await interaction.followup.send(file=discord_file, embed=embed)
        
        # Cleanup the temporary PNG file
        try:
            os.remove(png_path)
        except:
            pass
        
    except Exception as e:
        print(f"Map generation error: {e}")
        import traceback
        traceback.print_exc()
        await interaction.followup.send(f"❌ Error generating map: {str(e)}")

@bot.tree.command(name='surrender', description='Give up and reveal the answer')
async def surrender(interaction: discord.Interaction):
    """End the current game and reveal the answer"""
    channel_id = interaction.channel.id
    
    if channel_id not in active_games:
        await interaction.response.send_message("❌ No active game in progress!")
        return
    
    game = active_games[channel_id]
    target = game.target_country
    
    embed = discord.Embed(
        title="🏳️ Game Over",
        description=f"The country was: **{target['name']}**\n\n"
                    f"Better luck next time! Use `/start` for a new game.",
        color=discord.Color.dark_gray()
    )
    await interaction.response.send_message(embed=embed)
    del active_games[channel_id]

@bot.tree.command(name='stats', description='Show current game statistics')
async def show_stats(interaction: discord.Interaction):
    """Show statistics for the current game"""
    channel_id = interaction.channel.id
    
    if channel_id not in active_games:
        await interaction.response.send_message("❌ No active game in progress!")
        return
    
    game = active_games[channel_id]
    stats = game.get_stats()
    
    closest_text = f"{stats['closest_guess']} ({stats['closest_distance']:,.0f} km)" if stats['closest_guess'] else "None yet"
    
    embed = discord.Embed(
        title="📊 Game Statistics",
        description=f"**Guesses made:** {stats['guess_count']}\n"
                    f"**Players:** {', '.join(stats['players']) if stats['players'] else 'None'}\n"
                    f"**Closest guess:** {closest_text}",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument! Use `/help {ctx.command}` for usage info.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        print(f"Error: {error}")

if __name__ == '__main__':
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not found in .env file!")
    else:
        bot.run(TOKEN)
