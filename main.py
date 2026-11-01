import random
import discord
from discord import app_commands
from discord.ext import commands, tasks  
import datetime
import pretty_midi
import os
import sys
import time
import traceback

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# 初始化小達 (小龜)
bot = commands.Bot(command_prefix='/', intents=intents)

# 開發者/作者 ID 清單
DEVELOPER_IDS = [1187970337338572881] #⬅改成你的id id，這是我的

# 色號定義 (dadadadadadadadaa)
COLOR_TURTLE = 0x1BB80A   # 小達的主題色
COLOR_COOLDOWN = 0x75CAFF # 冷卻色號
COLOR_ERROR = 0xE00000    # 錯誤警告色號

# 回應
EIGHT_BALL_RESPONSES = [
    "好", "是", "不行", "可以", "行", "能", "不能",
    "so?", "恩可能是", "可能不是", "無法回答", "為什麼","恩", "and?", "那?", "否", "拒絕", "答應",
    "你覺得呢","我不知道", "你說的很對，但是又很不對", "問別人","這是個好問題","好","不好","聽起來不錯",
    "喔","虫合","蝦密","什麼?","哩喜勒工沙小","ok","達我願意","達我不願意","一氧化二氫","行","不行","ko","no","yes","bruh","huh","omg",
    "你應該要讓<@1480093857302577182>去看恐怖谷圖",
]

# 可選樂器對照表
INSTRUMENT_CHOICES = {
    "鋼琴 (Piano)": "Acoustic Grand Piano",
    "八音盒 (Music Box)": "Music Box",
    "木吉他 (Steel Guitar)": "Acoustic Guitar (steel)",
    "電吉他 (Electric Guitar)": "Electric Guitar (clean)",
    "小提琴 (Violin)": "Violin",
    "薩克斯風 (Saxophone)": "Alto Sax"
}

# 音樂風格設定檔
STYLE_CONFIGS = {
    "gentle": {
        "name": "溫和(平淡)",
        "scale": [60, 62, 64, 67, 69, 72, 74, 76],
        "chords": [[48, 52, 55], [45, 48, 52], [41, 45, 48], [43, 47, 50]],
        "rhythms": [1.0, 1.0, 0.5, 0.5, 2.0],
        "vel_range": (60, 85)
    },
    "intense": {
        "name": "刺激(緊張)",
        "scale": [60, 61, 63, 66, 67, 69, 72, 73, 75],
        "chords": [[48, 51, 54], [49, 52, 55], [42, 45, 48]],
        "rhythms": [0.25, 0.25, 0.5, 0.25],
        "vel_range": (85, 120)
    },
    "mysterious": {
        "name": "神秘(懸疑)",
        "scale": [60, 62, 64, 66, 68, 70, 72, 74],
        "chords": [[48, 52, 56], [46, 50, 54], [44, 48, 52]],
        "rhythms": [0.5, 1.5, 1.0, 2.0],
        "vel_range": (50, 95)
    },
    "thriller": {
        "name": "驚悚(恐怖)",
        "scale": [60, 61, 64, 65, 68, 69, 72, 73],
        "chords": [[36, 37, 48], [36, 42, 45], [38, 41, 44]],
        "rhythms": [0.25, 0.75, 1.5, 0.5],
        "vel_range": (40, 127)
    },
    "elegant": {
        "name": "高雅(優雅)",
        "scale": [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79],
        "chords": [[48, 52, 55], [45, 48, 52], [41, 45, 48], [43, 47, 50]],
        "rhythms": [1.0, 0.5, 0.5, 1.0],
        "vel_range": (70, 100)
    }
}

# 鼓組 MIDI 音高定義
KICK_DRUM = 36      # 大鼓
SNARE_DRUM = 38     # 小鼓
CLOSED_HIHAT = 42   # 閉合踩鑔
OPEN_HIHAT = 46     # 開放踩鑔
CRASH_CYMBAL = 49   # 鈸
HIGH_TOM = 50       # 高音筒鼓
LOW_TOM = 45        # 低音筒鼓

# 全域錯誤處理
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        embed = discord.Embed(
            title="⏱️ 技能冷卻中...",
            description=f"等達我一下下，給達我 **{error.retry_after:.1f}** 秒鐘，保證會回你，待會再跟達我說！",
            color=COLOR_COOLDOWN
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        error_msg = f"```{type(error).__name__}: {str(error)}```"
        embed = discord.Embed(
            title="🚨 指令執行發生錯誤！",
            description=f"小達遇到了一些狀況，請把下面的錯誤代碼提供給開發者：\n{error_msg}",
            color=COLOR_ERROR
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        print(f"指令發生未知錯誤: {error}")
        traceback.print_exc()

# 定義動態切換狀態的任務 (設定每 10 秒切換一次)
@tasks.loop(seconds=10)
async def change_status():
    if not bot.is_ready():
        return

    # 計算當前的延遲與伺服器數量
    latency = round(bot.latency * 1000)
    guild_count = len(bot.guilds)

    # 狀態訊息清單 (會在兩者之間輪流切換)
    statuses = [
        f"達我的反應速度為{latency}ms，還有能給達我零食嗎:>",
        f"達我在{guild_count}個伺服器逛逛"
    ]

    # 使用目前時間秒數來交替切換 index (0 或 1)
    status_index = int(time.time() // 10) % len(statuses)
    current_status = statuses[status_index]

    # 更新機器人的 Discord 狀態顯示 (正在玩/Playing)
    await bot.change_presence(activity=discord.Game(name=current_status))

@bot.event
async def on_ready():
    await bot.tree.sync()
    # 啟動動態狀態切換任務 (若尚未啟動)
    if not change_status.is_running():
        change_status.start()
    print(f'達我是 {bot.user} 已上線!!')


# =========================================================
# 1. INFO 分類指令群組：/info [...]
# =========================================================
info_group = app_commands.Group(name="info", description="查看使用者、伺服器與身分組相關資訊")

@info_group.command(name='使用者資訊', description='查看特定使用者或自己的詳細資訊')
@app_commands.describe(target='選擇要查看的使用者 (預設自己)')
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def user_info(interaction: discord.Interaction, target: discord.Member = None):
    member = target or interaction.user
    
    created_at = member.created_at.strftime("%Y-%m-%d %H:%M:%S")
    joined_at = member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "未知"
    
    embed = discord.Embed(
        title=f"👤 {member.display_name} 的個人資訊",
        color=COLOR_TURTLE
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="🏷️ 帳號名稱", value=str(member), inline=True)
    embed.add_field(name="🆔 User ID", value=str(member.id), inline=True)
    embed.add_field(name="⭐ 最高身分組", value=member.top_role.mention, inline=False)
    embed.add_field(name="📅 帳號建立時間", value=f"`{created_at}`", inline=True)
    embed.add_field(name="📥 加入伺服器時間", value=f"`{joined_at}`", inline=True)
    
    await interaction.response.send_message(embed=embed)

@info_group.command(name='伺服器資訊', description='查看當前伺服器的統計資訊')
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def server_info(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        embed = discord.Embed(
            title="⚠️ 錯誤", description="這個指令只能在伺服器中使用喔！skull(達我還不能這樣自由穿梭)", color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    created_at = guild.created_at.strftime("%Y-%m-%d %H:%M:%S")
    owner = guild.owner.mention if guild.owner else "未知"

    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)

    embed = discord.Embed(
        title=f"🏰 {guild.name} 伺服器資訊",
        color=COLOR_TURTLE
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
        
    embed.add_field(name="👑 伺服器擁有者", value=owner, inline=True)
    embed.add_field(name="🆔 伺服器 ID", value=str(guild.id), inline=True)
    embed.add_field(name="👥 總成員人數", value=f"**{guild.member_count}** 人", inline=True)
    embed.add_field(name="💬 文字頻道數", value=f"**{text_channels}** 個", inline=True)
    embed.add_field(name="🔊 語音頻道數", value=f"**{voice_channels}** 個", inline=True)
    embed.add_field(name="📅 伺服器建立時間", value=f"`{created_at}`", inline=False)

    await interaction.response.send_message(embed=embed)

@info_group.command(name='身分組資訊', description='查詢指定身分組的詳細資訊')
@app_commands.describe(role='選擇要查詢的身分組')
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def role_info(interaction: discord.Interaction, role: discord.Role):
    created_at = role.created_at.strftime("%Y-%m-%d %H:%M:%S")
    color_hex = f"#{role.color.value:06X}" if role.color.value else "預設色"

    embed = discord.Embed(
        title=f"🏷️ 身分組資訊：{role.name}",
        color=role.color if role.color.value else COLOR_TURTLE
    )
    embed.add_field(name="🆔 身分組 ID", value=f"`{role.id}`", inline=True)
    embed.add_field(name="🎨 色號 Hex", value=f"`{color_hex}`", inline=True)
    embed.add_field(name="👥 擁有此身分組人數", value=f"**{len(role.members)}** 人", inline=True)
    embed.add_field(name="🔔 是否可被提及", value="是" if role.mentionable else "否", inline=True)
    embed.add_field(name="📌 是否獨立顯示", value="是" if role.hoist else "否", inline=True)
    embed.add_field(name="📅 建立時間", value=f"`{created_at}`", inline=False)

    await interaction.response.send_message(embed=embed)

bot.tree.add_command(info_group)


# =========================================================
# 2. FUN 分類指令群組：/fun [...]
# =========================================================
fun_group = app_commands.Group(name="fun", description="娛樂與小遊戲(歐北亂玩)指令群組")

# 1. 說話 (改版：只發送一則訊息)
# 1. 說話 (簡化版：純粹轉述一則訊息)
@fun_group.command(name='說話', description='讓小達學你說話')
@app_commands.describe(message='學習的內容')
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def repeat(interaction: discord.Interaction, message: str):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 使用者ID: {interaction.user.id} ({interaction.user}) 使用了指令 [/fun 說話]")

    # 直接發送使用者輸入的訊息
    await interaction.response.send_message(message)

# 2. 疑問解答
@fun_group.command(name='疑問解答', description='問小達一個問題')
@app_commands.describe(question='告訴剛學會講話的小達你的疑問')
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def eight_ball(interaction: discord.Interaction, question: str):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 使用者ID: {interaction.user.id} ({interaction.user}) 使用了指令 [/fun 疑問解答]")

    response = random.choice(EIGHT_BALL_RESPONSES)
    embed = discord.Embed(
        title="🔮 剛學會講話的小達，來，解，答~",
        color=COLOR_TURTLE
    )
    embed.add_field(name="❓ 你的疑問", value=question, inline=False)
    embed.add_field(name="💡 達我的解答", value=response, inline=False)
    await interaction.response.send_message(embed=embed)

# 3. BMI 計算
@fun_group.command(name='bmi', description='計算你的體重 BMI 指數')
@app_commands.describe(height='身高 (單位: 公分 cm)', weight='體重 (單位: 公斤 kg)')
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def bmi_calc(interaction: discord.Interaction, height: float, weight: float):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 使用者ID: {interaction.user.id} ({interaction.user}) 使用了指令 [/fun bmi]")

    if height <= 0 or weight <= 0:
        embed = discord.Embed(
            title="⚠️ 別亂輸入，小達不懂",
            description="身高and體重必須大於0啦！我又不是來學數線的啦！",
            color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    height_m = height / 100.0
    bmi = weight / (height_m ** 2)

    if bmi < 18.5:
        status = "太輕了喔~"
        advice = "你好像比我還要輕"
    elif 18.5 <= bmi < 24:
        status = "正常耶"
        advice = "很棒喔！繼續保持！:)"
    elif 24 <= bmi < 27:
        status = "太重啦"
        advice = "注意一下下你的身體健康，我可是沒有胖過的！"
    else:
        status = "世界重量冠軍"
        advice = "達..達??恩..恭喜，過重了"

    embed = discord.Embed(
        title="⚖️ 小達BMI健康計算機",
        color=COLOR_TURTLE
    )
    embed.add_field(name="📏 身高", value=f"{height} cm", inline=True)
    embed.add_field(name="⚖️ 體重", value=f"{weight} kg", inline=True)
    embed.add_field(name="📊 BMI指數", value=f"**{bmi:.2f}**", inline=False)
    embed.add_field(name="🏷️ 評估結果", value=f"**{status}**", inline=True)
    embed.add_field(name="💡 小達評論", value=advice, inline=False)

    await interaction.response.send_message(embed=embed)

# 4. 取得使用者頭像
@fun_group.command(name='頭像', description='查看特定使用者或自己的高清大頭貼')
@app_commands.describe(target='選擇要查看頭像的人 (預設自己)')
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def avatar_cmd(interaction: discord.Interaction, target: discord.Member = None):
    member = target or interaction.user
    avatar_url = member.display_avatar.url

    embed = discord.Embed(
        title=f"🖼️ {member.display_name} 的大頭貼",
        color=COLOR_TURTLE
    )
    embed.set_image(url=avatar_url)
    embed.add_field(name="🔗 原圖連結", value=f"[點達我開啟高清圖片(好像也不太高清)]({avatar_url})", inline=False)

    await interaction.response.send_message(embed=embed)

# ---------------------------------------------------------
# 1A2B 猜數字小遊戲邏輯與介面
# ---------------------------------------------------------
class Game1A2B:
    def __init__(self, length=4, track_b=False):
        self.length = length
        self.track_b = track_b
        self.answer = "".join(random.sample("0123456789", length))
        self.history = []  # [(guess, a, b)]
        self.b_digits = set() # 記錄獲得過 B 的數字
        self.start_time = time.time()
        self.is_win = False

    def check_guess(self, guess: str):
        a = 0
        b = 0
        for i in range(self.length):
            if guess[i] == self.answer[i]:
                a += 1
            elif guess[i] in self.answer:
                b += 1
                if self.track_b:
                    self.b_digits.add(guess[i])
        
        self.history.append((guess, a, b))
        if a == self.length:
            self.is_win = True
        return a, b

class Modal1A2B(discord.ui.Modal, title="🔢 1A2B 猜數字）："):
    guess_input = discord.ui.TextInput(
        label="請輸入猜測數字",
        placeholder="請勿輸入重複數字",
        required=True
    )

    def __init__(self, game, user_id):
        super().__init__()
        self.game = game
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("別亂按別人的 1A2B 遊戲！", ephemeral=True)
            return

        guess = self.guess_input.value.strip()

        if len(guess) != self.game.length or not guess.isdigit() or len(set(guess)) != self.game.length:
            await interaction.response.send_message(
                f"❌ 輸入無效！請輸入 **{self.game.length} 個不重複的純數字**！", ephemeral=True
            )
            return

        a, b = self.game.check_guess(guess)
        elapsed = int(time.time() - self.game.start_time)

        # 建立主要遊戲 Embed
        embeds = []
        
        history_text = "\n".join([f"第 {i+1} 次: `{g}` ➔ **{ha}A {hb}B**" for i, (g, ha, hb) in enumerate(self.game.history)])
        if not history_text:
            history_text = "尚未開始猜測"

        if self.game.is_win:
            main_embed = discord.Embed(
                title=f"🎉 猜對了！答案就是 {self.game.answer}！",
                description=f"### 📜 猜測歷程\n{history_text}",
                color=COLOR_TURTLE
            )
            main_embed.add_field(name="⏱️ 總共耗時", value=f"**{elapsed}** 秒", inline=True)
            main_embed.add_field(name="🐾 總猜測次數", value=f"**{len(self.game.history)}** 次", inline=True)
            embeds.append(main_embed)

            if self.game.track_b:
                sorted_b = "".join(sorted(list(self.game.b_digits))) or "無"
                b_embed = discord.Embed(
                    title="🟡 B 數字紀錄庫",
                    description=f"目前提示過屬於 **B** 的數字為：\n`{sorted_b}`",
                    color=COLOR_TURTLE
                )
                embeds.append(b_embed)

            await interaction.response.edit_message(content="🎉 遊戲勝利！太厲害啦！", embeds=embeds, view=None)
        else:
            main_embed = discord.Embed(
                title=f"🔢 1A2B 戰局中 ({self.game.length} 個數字)",
                description=f"### 📜 猜測歷程\n{history_text}",
                color=COLOR_TURTLE
            )
            main_embed.set_footer(text=f"目前猜測次數: {len(self.game.history)} 次 | 已耗時: {elapsed} 秒")
            embeds.append(main_embed)

            if self.game.track_b:
                sorted_b = " ".join(sorted(list(self.game.b_digits))) or "暫無"
                b_embed = discord.Embed(
                    title="🟡 B 數字紀錄庫",
                    description=f"目前提示過屬於 **B** 的數字：\n`{sorted_b}`",
                    color=COLOR_TURTLE
                )
                embeds.append(b_embed)

            await interaction.response.edit_message(content=f"🎮 最新猜測：`{guess}` ➔ **{a}A {b}B**", embeds=embeds)

class View1A2B(discord.ui.View):
    def __init__(self, game, user_id):
        super().__init__(timeout=300)
        self.game = game
        self.user_id = user_id

    @discord.ui.button(label="🎲 猜測數字", style=discord.ButtonStyle.primary)
    async def guess_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("別亂按別人的 1A2B 遊戲！", ephemeral=True)
            return
        await interaction.response.send_modal(Modal1A2B(self.game, self.user_id))

# 5. 1A2B 指令
@fun_group.command(name='1a2b', description='開始一局 1A2B 猜數字小遊戲')
@app_commands.describe(
    length='要猜測的數字位數 (必填: 3 ~ 10 位數)',
    track_b='是否開啟「紀錄 B 數字」輔助功能？(選填，預設關閉)'
)
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def cmd_1a2b(interaction: discord.Interaction, length: int, track_b: bool = False):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 使用者ID: {interaction.user.id} ({interaction.user}) 使用了指令 [/fun 1a2b]")

    if length < 3 or length > 10:
        embed = discord.Embed(
            title="⚠️ 參數輸入錯誤",
            description="數字位數必須介於 **3 到 10** 個數字之間！",
            color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    game = Game1A2B(length=length, track_b=track_b)

    embeds = []
    main_embed = discord.Embed(
        title=f"🔢 1A2B 猜數字小遊戲開始！({length} 個數字)",
        description="點擊下方按鈕開始猜測！每次請輸入不重複的數字喔！",
        color=COLOR_TURTLE
    )
    main_embed.set_footer(text="A 代表數字與位置皆正確 | B 代表數字正確但位置錯誤")
    embeds.append(main_embed)

    if track_b:
        b_embed = discord.Embed(
            title="🟡 B 數字紀錄庫",
            description="目前提示過屬於 **B** 的數字：\n`暫無`",
            color=COLOR_TURTLE
        )
        embeds.append(b_embed)

    view = View1A2B(game, interaction.user.id)
    await interaction.response.send_message(embeds=embeds, view=view)

# ---------------------------------------------------------
# 踩地雷 (Minesweeper) 邏輯與介面
# ---------------------------------------------------------
NUM_EMOJIS = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

class MinesweeperGame:
    def __init__(self, rows=6, cols=6, mines=6):
        self.rows = rows
        self.cols = cols
        self.num_mines = mines
        self.board = [[0 for _ in range(cols)] for _ in range(rows)]
        self.mines = set()
        self.revealed = [[False for _ in range(cols)] for _ in range(rows)]
        self.flags = set()
        self.initialized = False
        self.start_time = time.time()
        self.is_over = False
        self.is_win = False

    def initialize_mines(self, safe_r, safe_c):
        safe_zone = {
            (safe_r + dr, safe_c + dc)
            for dr in [-1, 0, 1]
            for dc in [-1, 0, 1]
            if 0 <= safe_r + dr < self.rows and 0 <= safe_c + dc < self.cols
        }
        
        available = [
            (r, c) for r in range(self.rows) for c in range(self.cols)
            if (r, c) not in safe_zone
        ]
        
        actual_mines = min(self.num_mines, len(available))
        self.mines = set(random.sample(available, actual_mines))
        
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) in self.mines:
                    continue
                count = sum(1 for dr in [-1,0,1] for dc in [-1,0,1] 
                            if (dr != 0 or dc != 0) and (r+dr, c+dc) in self.mines)
                self.board[r][c] = count
        self.initialized = True

    def reveal(self, r, c):
        if not self.initialized:
            self.initialize_mines(r, c)
            
        if (r, c) in self.flags or self.revealed[r][c]:
            return True

        if (r, c) in self.mines:
            self.revealed[r][c] = True
            self.is_over = True
            self.is_win = False
            return False

        queue = [(r, c)]
        while queue:
            curr_r, curr_c = queue.pop(0)
            if self.revealed[curr_r][curr_c]:
                continue
            self.revealed[curr_r][curr_c] = True
            if (curr_r, curr_c) in self.flags:
                self.flags.remove((curr_r, curr_c))

            if self.board[curr_r][curr_c] == 0:
                for dr in [-1,0,1]:
                    for dc in [-1,0,1]:
                        nr, nc = curr_r + dr, curr_c + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols and not self.revealed[nr][nc]:
                            queue.append((nr, nc))

        unrevealed_non_mines = sum(1 for r in range(self.rows) for c in range(self.cols) 
                                   if not self.revealed[r][c] and (r, c) not in self.mines)
        if unrevealed_non_mines == 0:
            self.is_over = True
            self.is_win = True

        return True

    def toggle_flag(self, r, c):
        if self.revealed[r][c]:
            return
        if (r, c) in self.flags:
            self.flags.remove((r, c))
        else:
            self.flags.add((r, c))

    def auto_deduce(self):
        if not self.flags:
            return False, "請至少先放置一個旗子 🚩 才能使用自動推演功能喔！(你插錯不關達我的事情，但達我會給你翻錯的)"

        changed = False
        for r in range(self.rows):
            for c in range(self.cols):
                if self.revealed[r][c] and self.board[r][c] > 0:
                    neighbors = [(r+dr, c+dc) for dr in [-1,0,1] for dc in [-1,0,1] 
                                 if (dr!=0 or dc!=0) and 0 <= r+dr < self.rows and 0 <= c+dc < self.cols]
                    flagged_neighbors = [p for p in neighbors if p in self.flags]

                    if len(flagged_neighbors) == self.board[r][c]:
                        unrevealed_neighbors = [p for p in neighbors if not self.revealed[p[0]][p[1]] and p not in self.flags]
                        for nr, nc in unrevealed_neighbors:
                            success = self.reveal(nr, nc)
                            changed = True
                            if not success:
                                return True, "炸了，恭喜！！"

        if not changed:
            return False, "目前狀況無法推演出安全格子，請嘗試繼續手動分析！"
        return True, "推演成功！"

    def render_board(self):
        header = "   " + " ".join([chr(97+c) for c in range(self.cols)]) + "\n"
        lines = [header]
        for r in range(self.rows):
            line = f"{r+1} "
            for c in range(self.cols):
                if self.revealed[r][c]:
                    if (r, c) in self.mines:
                        line += "💣"
                    else:
                        line += NUM_EMOJIS[self.board[r][c]]
                elif (r, c) in self.flags:
                    line += "🚩"
                else:
                    line += "🔲"
            lines.append(line)
        return "```\n" + "\n".join(lines) + "\n```"

class MinesweeperMoveModal(discord.ui.Modal, title="💣 踩地雷操作選單"):
    pos_input = discord.ui.TextInput(
        label="請輸入棋盤位置 (格式: 橫軸,縱軸 如: a,1)",
        placeholder="a,1",
        required=True
    )
    flag_input = discord.ui.TextInput(
        label="是否要插/拔旗子？ (y/n，預設 n)",
        placeholder="n",
        default="n",
        required=False
    )

    def __init__(self, game, message_user_id):
        super().__init__()
        self.game = game
        self.message_user_id = message_user_id

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.message_user_id:
            await interaction.response.send_message("哥..讓我和他玩玩吧，別插手攪局", ephemeral=True)
            return

        try:
            raw_pos = self.pos_input.value.strip().lower()
            parts = [p.strip() for p in raw_pos.replace("，", ",").split(",")]
            col_char, row_char = parts[0], parts[1]
            c = ord(col_char) - 97
            r = int(row_char) - 1

            if not (0 <= r < self.game.rows and 0 <= c < self.game.cols):
                raise ValueError
        except Exception:
            await interaction.response.send_message("位置格式輸入錯誤！請輸入如 `a,1` 格式。", ephemeral=True)
            return

        is_flag = self.flag_input.value.strip().lower() == "y"

        if is_flag:
            self.game.toggle_flag(r, c)
            msg = f"已在 `{col_char},{row_char}` 放置/移除旗子 🚩"
        else:
            success = self.game.reveal(r, c)
            msg = f"翻開了位置 `{col_char},{row_char}`" if success else "💣 踩到地雷囉！"

        elapsed = int(time.time() - self.game.start_time)

        if self.game.is_over:
            for mr, mc in self.game.mines:
                self.game.revealed[mr][mc] = True

            if self.game.is_win:
                embed = discord.Embed(
                    title="🎉 恭喜勝利！你成功清除了所有地雷！",
                    description=self.game.render_board(),
                    color=COLOR_TURTLE
                )
                await interaction.response.edit_message(content=f"⏱️ 遊戲結束！總共耗時：**{elapsed} 秒**", embed=embed, view=None)
            else:
                embed = discord.Embed(
                    title="💥 砰！炸了！哥們遊戲結束",
                    description=self.game.render_board(),
                    color=COLOR_ERROR
                )
                await interaction.response.edit_message(content=f"⏱️ 遊戲結束！總共耗時：**{elapsed} 秒**(但還是輸了)", embed=embed, view=None)
        else:
            embed = discord.Embed(
                title="💣 踩地雷戰局中",
                description=self.game.render_board(),
                color=COLOR_TURTLE
            )
            embed.set_footer(text=f"旗子數: {len(self.game.flags)} | 已耗時: {elapsed} 秒")
            await interaction.response.edit_message(content=f"🎮 {msg}", embed=embed)

class MinesweeperView(discord.ui.View):
    def __init__(self, game, user_id):
        super().__init__(timeout=300)
        self.game = game
        self.user_id = user_id

    @discord.ui.button(label="⛏️選擇位置", style=discord.ButtonStyle.primary)
    async def op_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("別幫他，這是達我與他之間的對戰..", ephemeral=True)
            return
        await interaction.response.send_modal(MinesweeperMoveModal(self.game, self.user_id))

    @discord.ui.button(label="💡 自動推演", style=discord.ButtonStyle.secondary)
    async def deduce_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("班長！！這裡有人學豬叫！！-xiaoxiao小小(看了名言後，有沒有放下不要亂按別的東西的心頭)", ephemeral=True)
            return

        success, result_msg = self.game.auto_deduce()
        elapsed = int(time.time() - self.game.start_time)

        if self.game.is_over:
            for mr, mc in self.game.mines:
                self.game.revealed[mr][mc] = True

            if self.game.is_win:
                embed = discord.Embed(
                    title="🎉 恭喜勝利！(達我悲哀)推演完成並成功清除地雷！",
                    description=self.game.render_board(),
                    color=COLOR_TURTLE
                )
                await interaction.response.edit_message(content=f"⏱️ 遊戲結束！總共耗時：**{elapsed} 秒**", embed=embed, view=None)
            else:
                embed = discord.Embed(
                    title="💥 自動推演踩到地雷爆炸了(達我樂極)！(旗子標錯位置了喔)",
                    description=self.game.render_board(),
                    color=COLOR_ERROR
                )
                await interaction.response.edit_message(content=f"⏱️ 遊戲結束！總共耗時：**{elapsed} 秒**", embed=embed, view=None)
        else:
            embed = discord.Embed(
                title="💣 踩地雷戰局中",
                description=self.game.render_board(),
                color=COLOR_TURTLE
            )
            embed.set_footer(text=f"旗子數: {len(self.game.flags)} | 已耗時: {elapsed} 秒")
            await interaction.response.edit_message(content=f"💡 自動推演結果: {result_msg}", embed=embed)

    @discord.ui.button(label="🔄 刷新超時時間", style=discord.ButtonStyle.success)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("別亂按別人的刷新按鈕喔！", ephemeral=True)
            return
        
        elapsed = int(time.time() - self.game.start_time)
        embed = discord.Embed(
            title="💣 踩地雷戰局中",
            description=self.game.render_board(),
            color=COLOR_TURTLE
        )
        embed.set_footer(text=f"旗子數: {len(self.game.flags)} | 已耗時: {elapsed} 秒")
        await interaction.response.edit_message(content="🔄 系統防呆結束時間已重新刷新！您可以繼續思考 5 分鐘！", embed=embed)

# 6. 踩地雷指令
@fun_group.command(name='踩地雷', description='開始一局 6x6 文字版踩地雷小遊戲')
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def minesweeper_cmd(interaction: discord.Interaction):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 使用者ID: {interaction.user.id} ({interaction.user}) 使用了指令 [/fun 踩地雷]")

    game = MinesweeperGame(rows=6, cols=6, mines=6)
    embed = discord.Embed(
        title="💣 踩地雷小遊戲開始！",
        description=game.render_board(),
        color=COLOR_TURTLE
    )
    embed.set_footer(text="請點擊下方【⛏️ 操作位置】輸入座標 (如 a,1) 開始遊戲，首按保證安全！")

    view = MinesweeperView(game, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)

# ---------------------------------------------------------
# 2048 小遊戲邏輯與介面
# ---------------------------------------------------------
class Game2048:
    def __init__(self):
        self.grid = [[0]*4 for _ in range(4)]
        self.score = 0
        self.moves = 0
        self.start_time = time.time()
        self.is_over = False
        self.is_win = False
        self.spawn_tile()
        self.spawn_tile()

    def spawn_tile(self):
        empty = [(r, c) for r in range(4) for c in range(4) if self.grid[r][c] == 0]
        if empty:
            r, c = random.choice(empty)
            self.grid[r][c] = 4 if random.random() < 0.1 else 2

    def move(self, direction):
        moved = False
        
        def slide_left(row):
            nonlocal moved
            new_row = [i for i in row if i != 0]
            for i in range(len(new_row)-1):
                if new_row[i] == new_row[i+1]:
                    new_row[i] *= 2
                    self.score += new_row[i]
                    if new_row[i] == 2048:
                        self.is_win = True
                    new_row[i+1] = 0
            new_row = [i for i in new_row if i != 0]
            new_row += [0]*(4 - len(new_row))
            if new_row != row:
                moved = True
            return new_row

        if direction == 'left':
            for r in range(4):
                self.grid[r] = slide_left(self.grid[r])
        elif direction == 'right':
            for r in range(4):
                rev = self.grid[r][::-1]
                res = slide_left(rev)
                self.grid[r] = res[::-1]
        elif direction == 'up':
            for c in range(4):
                col = [self.grid[r][c] for r in range(4)]
                res = slide_left(col)
                for r in range(4):
                    self.grid[r][c] = res[r]
        elif direction == 'down':
            for c in range(4):
                col = [self.grid[r][c] for r in range(4)][::-1]
                res = slide_left(col)
                res = res[::-1]
                for r in range(4):
                    self.grid[r][c] = res[r]

        if moved:
            self.moves += 1
            self.spawn_tile()
            self.check_game_over()

    def check_game_over(self):
        for r in range(4):
            for c in range(4):
                if self.grid[r][c] == 0:
                    return
                if c < 3 and self.grid[r][c] == self.grid[r][c+1]:
                    return
                if r < 3 and self.grid[r][c] == self.grid[r+1][c]:
                    return
        self.is_over = True

    def render_board(self):
        lines = []
        for row in self.grid:
            line_str = " ".join([f"{val:4d}" if val != 0 else "   ." for val in row])
            lines.append(line_str)
        return "```\n" + "\n".join(lines) + "\n```"

class View2048(discord.ui.View):
    def __init__(self, game, user_id):
        super().__init__(timeout=300)
        self.game = game
        self.user_id = user_id

    async def process_move(self, interaction: discord.Interaction, direction: str):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("達我正在給他玩，你不要亂動！", ephemeral=True)
            return

        self.game.move(direction)
        elapsed = int(time.time() - self.game.start_time)

        if self.game.is_win and not self.game.is_over:
            embed = discord.Embed(
                title="🎉 恭喜玩家！成功合成 2048！",
                description=self.game.render_board(),
                color=COLOR_TURTLE
            )
            embed.add_field(name="🏆 得分 (Score)", value=f"**{self.game.score}**", inline=True)
            embed.add_field(name="👣 移動次數", value=f"**{self.game.moves}** 次", inline=True)
            embed.add_field(name="⏱️ 總耗時", value=f"**{elapsed}** 秒", inline=True)
            await interaction.response.edit_message(content="🎉 你合出了 2048！好強！", embed=embed, view=None)
            return

        if self.game.is_over:
            embed = discord.Embed(
                title="PA！移動不了！2048 遊戲結束！",
                description=self.game.render_board(),
                color=COLOR_ERROR
            )
            embed.add_field(name="🏆 最終得分", value=f"**{self.game.score}**", inline=True)
            embed.add_field(name="👣 移動次數", value=f"**{self.game.moves}** 次", inline=True)
            embed.add_field(name="⏱️ 總耗時", value=f"**{elapsed}** 秒", inline=True)
            await interaction.response.edit_message(content="🎮 遊戲結束！沒位置可移動囉！", embed=embed, view=None)
            return

        embed = discord.Embed(
            title="🎮 2048 遊戲中",
            description=self.game.render_board(),
            color=COLOR_TURTLE
        )
        embed.add_field(name="🏆 得分 (Score)", value=f"**{self.game.score}**", inline=True)
        embed.add_field(name="👣 移動次數", value=f"**{self.game.moves}** 次", inline=True)
        embed.set_footer(text=f"遊玩時間: {elapsed} 秒")
        await interaction.response.edit_message(content="請使用下方方向鍵滑動：", embed=embed)

    @discord.ui.button(label="⬆️", style=discord.ButtonStyle.primary, row=0)
    async def up_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_move(interaction, 'up')

    @discord.ui.button(label="⬇️", style=discord.ButtonStyle.primary, row=0)
    async def down_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_move(interaction, 'down')

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary, row=0)
    async def left_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_move(interaction, 'left')

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary, row=0)
    async def right_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_move(interaction, 'right')

    @discord.ui.button(label="🔄 刷新超時時間", style=discord.ButtonStyle.success, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("哥們...手很貝戈戈", ephemeral=True)
            return
        
        elapsed = int(time.time() - self.game.start_time)
        embed = discord.Embed(
            title="🎮 2048 遊戲中",
            description=self.game.render_board(),
            color=COLOR_TURTLE
        )
        embed.add_field(name="🏆 得分 (Score)", value=f"**{self.game.score}**", inline=True)
        embed.add_field(name="👣 移動次數", value=f"**{self.game.moves}** 次", inline=True)
        embed.set_footer(text=f"遊玩時間: {elapsed} 秒")
        await interaction.response.edit_message(content="🔄 系統防發呆結束時間已重新刷新！您可以繼續思考 5 分鐘！", embed=embed)

# 7. 2048 指令
@fun_group.command(name='2048', description='開始一局 2048 數字拼圖小遊戲')
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def cmd_2048(interaction: discord.Interaction):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 使用者ID: {interaction.user.id} ({interaction.user}) 使用了指令 [/fun 2048]")

    game = Game2048()
    embed = discord.Embed(
        title="🎮 2048 遊戲開始！",
        description=game.render_board(),
        color=COLOR_TURTLE
    )
    embed.add_field(name="🏆 得分 (Score)", value=f"**{game.score}**", inline=True)
    embed.add_field(name="👣 移動次數", value=f"**{game.moves}** 次", inline=True)
    embed.set_footer(text="點擊下方方向按鈕滑動數字，合成出 2048 吧！")

    view = View2048(game, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)

bot.tree.add_command(fun_group)


# =========================================================
# 3. MIDI 分類指令群組：/midi [...]
# =========================================================
midi_group = app_commands.Group(name="midi", description="小達的 MIDI 音樂創作大師群組指令")

@midi_group.command(name='鋼琴曲', description='達我，小達，用爪子幫你細細的亂寫曲，你可要好好感謝達我歐~')
@app_commands.describe(
    notes='跟達我說你要多少音符(5~100之間)',
    bpm='跟達我說你要多少BPM(達我通常用120(最多30~300之間(含))',
    instrument='選一個樂器讓小達幫你演奏(達我通常用鋼琴)'
)
@app_commands.choices(
    instrument=[
        app_commands.Choice(name=name, value=value)
        for name, value in INSTRUMENT_CHOICES.items()
    ]
)
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def random_midi(
    interaction: discord.Interaction, 
    notes: int, 
    bpm: int = 120,
    instrument: app_commands.Choice[str] = None
):
    selected_instrument_name = instrument.value if instrument else "Acoustic Grand Piano"
    display_name = instrument.name if instrument else "鋼琴 (Piano)"

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 使用者ID: {interaction.user.id} ({interaction.user}) 使用了指令 [/midi 鋼琴曲]")

    if notes < 5 or notes > 100:
        embed = discord.Embed(
            title="⚠️ 參數輸入錯誤",
            description="欸欸，達我的爪子已經斷了幾根，手很挑剔，你叫達我寫的音符數量必須介於5到100之間",
            color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if bpm < 30 or bpm > 300:
        embed = discord.Embed(
            title="⚠️ 參數輸入錯誤",
            description="BPM最多在30~300之間(含)不然我心臟會受不了AHH",
            color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer()

    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst_program = pretty_midi.instrument_name_to_program(selected_instrument_name)
    inst_obj = pretty_midi.Instrument(program=inst_program)

    seconds_per_beat = 60.0 / bpm
    current_time = 0.0
    for _ in range(notes):
        pitch = random.randint(48, 84)
        beats_duration = random.uniform(0.5, 2.0)
        duration = beats_duration * seconds_per_beat
        velocity = random.randint(60, 110)

        note = pretty_midi.Note(
            velocity=velocity,
            pitch=pitch,
            start=current_time,
            end=current_time + duration
        )
        inst_obj.notes.append(note)
        current_time += duration + (random.uniform(0.0, 0.5) * seconds_per_beat)

    midi.instruments.append(inst_obj)

    file_path = f"random_{interaction.user.id}.mid"
    midi.write(file_path)

    try:
        discord_file = discord.File(file_path, filename=f"好聽的小達爪子亂彈，共{notes}個音符和{bpm}bpm.mid")
        embed = discord.Embed(
            title="🎹 爪子亂彈 MIDI 鋼琴曲出爐",
            description=f"待會跟達我說用 **{display_name}** 彈有 **{notes}** 個音符 + 有 **{bpm} BPM** 的 midi 有多好聽🎵",
            color=COLOR_TURTLE
        )
        await interaction.followup.send(embed=embed, file=discord_file)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@midi_group.command(name='pro', description='小達用剛掉下來的指甲創作一小段音樂:)(本地生成，不使用ai token)')
@app_commands.describe(
    bars='小節數 (2 ~ 30 小節，我都寫 4 小節)',
    bpm='音樂速度 BPM (達我都用 120)',
    instrument='樂器選擇 (達我都用 鋼琴)',
    style='音樂風格(達我通常選 溫和(平淡))',
    melody_only='是否只需純主旋律(不需要伴奏和弦)？(如果你不說，達我就當作你都要)'
)
@app_commands.choices(
    instrument=[
        app_commands.Choice(name=name, value=value)
        for name, value in INSTRUMENT_CHOICES.items()
    ],
    style=[
        app_commands.Choice(name="溫和 (平淡)", value="gentle"),
        app_commands.Choice(name="刺激 (緊張)", value="intense"),
        app_commands.Choice(name="神秘 (懸疑)", value="mysterious"),
        app_commands.Choice(name="驚悚 (恐怖)", value="thriller"),
        app_commands.Choice(name="高雅 (優雅)", value="elegant")
    ]
)
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def full_midi(
    interaction: discord.Interaction,
    bars: int = 4,
    bpm: int = 120,
    instrument: app_commands.Choice[str] = None,
    style: app_commands.Choice[str] = None,
    melody_only: bool = False
):
    selected_instrument_name = instrument.value if instrument else "Acoustic Grand Piano"
    display_name = instrument.name if instrument else "鋼琴 (Piano)"
    
    selected_style_key = style.value if style else "gentle"
    style_cfg = STYLE_CONFIGS[selected_style_key]

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 使用者ID: {interaction.user.id} ({interaction.user}) 使用了指令 [/midi pro] - 風格={style_cfg['name']}, 只留旋律={melody_only}")

    if bars < 2 or bars > 30:
        embed = discord.Embed(
            title="⚠️ 參數輸入錯誤",
            description="小節數只能在2~30之間喔，不然達我發揮不了",
            color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if bpm < 30 or bpm > 300:
        embed = discord.Embed(
            title="⚠️ 參數輸入錯誤",
            description="BPM最多在30~300之間(含)不然達我心臟會受不了AHH",
            color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer()

    key_shift = random.randint(0, 7)

    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst_program = pretty_midi.instrument_name_to_program(selected_instrument_name)
    inst_obj = pretty_midi.Instrument(program=inst_program)

    seconds_per_beat = 60.0 / bpm
    seconds_per_bar = seconds_per_beat * 4

    current_time = 0.0

    for i in range(bars):
        if not melody_only:
            chord_notes = style_cfg["chords"][i % len(style_cfg["chords"])]
            for chord_pitch in chord_notes:
                note = pretty_midi.Note(
                    velocity=max(40, style_cfg["vel_range"][0] - 15),
                    pitch=chord_pitch + key_shift,
                    start=current_time,
                    end=current_time + seconds_per_bar
                )
                inst_obj.notes.append(note)

        melody_time = current_time
        bar_end = current_time + seconds_per_bar

        while melody_time < bar_end:
            base_pitch = random.choice(style_cfg["scale"]) + key_shift
            octave_shift = random.choice([0, 0, 12, -12])
            pitch = max(36, min(96, base_pitch + octave_shift))

            duration_beats = random.choice(style_cfg["rhythms"])
            duration_sec = duration_beats * seconds_per_beat

            if melody_time + duration_sec > bar_end:
                duration_sec = bar_end - melody_time

            velocity = random.randint(style_cfg["vel_range"][0], style_cfg["vel_range"][1])

            note = pretty_midi.Note(
                velocity=velocity,
                pitch=pitch,
                start=melody_time,
                end=melody_time + duration_sec
            )
            inst_obj.notes.append(note)
            melody_time += duration_sec

        current_time += seconds_per_bar

    midi.instruments.append(inst_obj)

    file_path = f"full_{interaction.user.id}.mid"
    midi.write(file_path)

    chord_status_text = "純主旋律" if melody_only else "含伴奏和弦"

    try:
        discord_file = discord.File(file_path, filename=f"達我做的{style_cfg['name']}_{bars}小節_{bpm}bpm.mid")
        embed = discord.Embed(
            title=f"✨ 小達創作的【{style_cfg['name']}】風格樂曲！",
            description=f"依照你想要的，樂器是 **{display_name}**，風格是 **{chord_status_text}**，共有 **{bars} 小節** 和 **{bpm} BPM** 🎵",
            color=COLOR_TURTLE
        )
        await interaction.followup.send(embed=embed, file=discord_file)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@midi_group.command(name='爵士鼓', description='小達用尾巴甩鼓幫你打一段有節奏感的爵士鼓動感節奏')
@app_commands.describe(
    bars='小節數 (選在2~30小節，達我通常都用個4小節)',
    bpm='音樂速度 BPM (達我通常都用120)'
)
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def drum_midi(
    interaction: discord.Interaction,
    bars: int = 4,
    bpm: int = 120
):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 使用者ID: {interaction.user.id} ({interaction.user}) 使用了指令 [/midi 爵士鼓]")

    if bars < 2 or bars > 30:
        embed = discord.Embed(
            title="⚠️ 參數輸入錯誤",
            description="小節數只能在 2 到 30 小節之間喔！",
            color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if bpm < 30 or bpm > 300:
        embed = discord.Embed(
            title="⚠️ 參數輸入錯誤",
            description="BPM最多在30~300之間(含)不然達我心臟會受不了AHH",
            color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer()

    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    drum_inst = pretty_midi.Instrument(program=0, is_drum=True, name="Drums")

    seconds_per_beat = 60.0 / bpm
    step_sec = seconds_per_beat / 4

    kick_steps = {0}
    kick_steps.update(random.sample(range(1, 16), random.randint(2, 4)))
    snare_steps = set(random.sample([4, 12, random.randint(1, 15)], random.randint(2, 3)))
    hihat_density = random.choice(["8th", "16th", "syncopated"])

    current_time = 0.0

    for bar in range(bars):
        if bar == 0:
            drum_inst.notes.append(
                pretty_midi.Note(velocity=105, pitch=CRASH_CYMBAL, start=current_time, end=current_time + step_sec)
            )

        is_fill_in_bar = (bar > 0 and (bar + 1) % 4 == 0)

        for step in range(16):
            t = current_time + (step * step_sec)

            if is_fill_in_bar and step >= 12:
                tom_pitch = HIGH_TOM if step < 14 else LOW_TOM
                drum_inst.notes.append(
                    pretty_midi.Note(velocity=random.randint(95, 115), pitch=tom_pitch, start=t, end=t + step_sec)
                )
                continue

            if step in kick_steps or (random.random() < 0.1):
                drum_inst.notes.append(
                    pretty_midi.Note(velocity=random.randint(95, 120), pitch=KICK_DRUM, start=t, end=t + step_sec)
                )

            if step in snare_steps:
                drum_inst.notes.append(
                    pretty_midi.Note(velocity=random.randint(100, 125), pitch=SNARE_DRUM, start=t, end=t + step_sec)
                )
            elif random.random() < 0.08:
                drum_inst.notes.append(
                    pretty_midi.Note(velocity=random.randint(40, 65), pitch=SNARE_DRUM, start=t, end=t + step_sec)
                )

            should_play_hihat = False
            if hihat_density == "8th" and step % 2 == 0:
                should_play_hihat = True
            elif hihat_density == "16th":
                should_play_hihat = True
            elif hihat_density == "syncopated" and (step % 2 == 0 or random.random() < 0.3):
                should_play_hihat = True

            if should_play_hihat:
                hihat_pitch = OPEN_HIHAT if (step == 14 and random.random() < 0.5) else CLOSED_HIHAT
                drum_inst.notes.append(
                    pretty_midi.Note(velocity=random.randint(65, 95), pitch=hihat_pitch, start=t, end=t + step_sec)
                )

        current_time += 16 * step_sec

    midi.instruments.append(drum_inst)

    file_path = f"drum_{interaction.user.id}.mid"
    midi.write(file_path)

    try:
        discord_file = discord.File(file_path, filename=f"小達獨家隨機爵士鼓_{bars}小節_{bpm}bpm.mid")
        embed = discord.Embed(
            title="🥁 小達獨家隨機節奏爵士鼓",
            description=f"小達用尾巴打出了獨一無二的隨機節奏鼓組🥁\n懶得多說了，反正共 **{bars} 小節**、**{bpm} BPM**，呼呼，快累死達我了sob*",
            color=COLOR_TURTLE
        )
        await interaction.followup.send(embed=embed, file=discord_file)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@midi_group.command(name='合奏', description='小達認真囉！爪子玩旋律與尾巴打鼓一起演奏！')
@app_commands.describe(
    bars='小節數 (2 ~ 30 小節，預設 4 小節)',
    bpm='音樂速度 BPM (預設 120)',
    instrument='旋律樂器選擇 (預設: 鋼琴)',
    style='音樂風格 (預設: 溫和(平淡))'
)
@app_commands.choices(
    instrument=[
        app_commands.Choice(name=name, value=value)
        for name, value in INSTRUMENT_CHOICES.items()
    ],
    style=[
        app_commands.Choice(name="溫和 (平淡)", value="gentle"),
        app_commands.Choice(name="刺激 (緊張)", value="intense"),
        app_commands.Choice(name="神秘 (懸疑)", value="mysterious"),
        app_commands.Choice(name="驚悚 (恐怖)", value="thriller"),
        app_commands.Choice(name="高雅 (優雅)", value="elegant")
    ]
)
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def ensemble_midi(
    interaction: discord.Interaction,
    bars: int = 4,
    bpm: int = 120,
    instrument: app_commands.Choice[str] = None,
    style: app_commands.Choice[str] = None
):
    selected_instrument_name = instrument.value if instrument else "Acoustic Grand Piano"
    display_name = instrument.name if instrument else "鋼琴 (Piano)"
    
    selected_style_key = style.value if style else "gentle"
    style_cfg = STYLE_CONFIGS[selected_style_key]

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 使用者ID: {interaction.user.id} ({interaction.user}) 使用了指令 [/midi 合奏]")

    if bars < 2 or bars > 30:
        embed = discord.Embed(
            title="⚠️ 參數輸入錯誤",
            description="小節數只能在2~30之間喔，不然達我發揮不了",
            color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if bpm < 30 or bpm > 300:
        embed = discord.Embed(
            title="⚠️ 參數輸入錯誤",
            description="BPM最多在30~300之間(含)不然達我心臟會受不了AHH",
            color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer()

    key_shift = random.randint(0, 7)
    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)

    inst_program = pretty_midi.instrument_name_to_program(selected_instrument_name)
    inst_obj = pretty_midi.Instrument(program=inst_program, name="Melody & Chords")
    drum_inst = pretty_midi.Instrument(program=0, is_drum=True, name="Drums")

    seconds_per_beat = 60.0 / bpm
    seconds_per_bar = seconds_per_beat * 4
    step_sec = seconds_per_beat / 4

    kick_steps = {0}
    kick_steps.update(random.sample(range(1, 16), random.randint(2, 4)))
    snare_steps = set(random.sample([4, 12, random.randint(1, 15)], random.randint(2, 3)))
    hihat_density = random.choice(["8th", "16th", "syncopated"])

    current_time = 0.0

    for i in range(bars):
        chord_notes = style_cfg["chords"][i % len(style_cfg["chords"])]
        for chord_pitch in chord_notes:
            note = pretty_midi.Note(
                velocity=max(40, style_cfg["vel_range"][0] - 15),
                pitch=chord_pitch + key_shift,
                start=current_time,
                end=current_time + seconds_per_bar
            )
            inst_obj.notes.append(note)

        melody_time = current_time
        bar_end = current_time + seconds_per_bar
        while melody_time < bar_end:
            base_pitch = random.choice(style_cfg["scale"]) + key_shift
            octave_shift = random.choice([0, 0, 12, -12])
            pitch = max(36, min(96, base_pitch + octave_shift))

            duration_beats = random.choice(style_cfg["rhythms"])
            duration_sec = duration_beats * seconds_per_beat

            if melody_time + duration_sec > bar_end:
                duration_sec = bar_end - melody_time

            velocity = random.randint(style_cfg["vel_range"][0], style_cfg["vel_range"][1])
            note = pretty_midi.Note(
                velocity=velocity,
                pitch=pitch,
                start=melody_time,
                end=melody_time + duration_sec
            )
            inst_obj.notes.append(note)
            melody_time += duration_sec

        if i == 0:
            drum_inst.notes.append(
                pretty_midi.Note(velocity=105, pitch=CRASH_CYMBAL, start=current_time, end=current_time + step_sec)
            )

        is_fill_in_bar = (i > 0 and (i + 1) % 4 == 0)

        for step in range(16):
            t = current_time + (step * step_sec)

            if is_fill_in_bar and step >= 12:
                tom_pitch = HIGH_TOM if step < 14 else LOW_TOM
                drum_inst.notes.append(
                    pretty_midi.Note(velocity=random.randint(95, 115), pitch=tom_pitch, start=t, end=t + step_sec)
                )
                continue

            if step in kick_steps or (random.random() < 0.1):
                drum_inst.notes.append(
                    pretty_midi.Note(velocity=random.randint(95, 120), pitch=KICK_DRUM, start=t, end=t + step_sec)
                )

            if step in snare_steps:
                drum_inst.notes.append(
                    pretty_midi.Note(velocity=random.randint(100, 125), pitch=SNARE_DRUM, start=t, end=t + step_sec)
                )

            should_play_hihat = (hihat_density == "8th" and step % 2 == 0) or (hihat_density == "16th") or (hihat_density == "syncopated" and (step % 2 == 0 or random.random() < 0.3))
            if should_play_hihat:
                hihat_pitch = OPEN_HIHAT if (step == 14 and random.random() < 0.5) else CLOSED_HIHAT
                drum_inst.notes.append(
                    pretty_midi.Note(velocity=random.randint(65, 95), pitch=hihat_pitch, start=t, end=t + step_sec)
                )

        current_time += seconds_per_bar

    midi.instruments.append(inst_obj)
    midi.instruments.append(drum_inst)

    file_path = f"ensemble_{interaction.user.id}.mid"
    midi.write(file_path)

    try:
        discord_file = discord.File(file_path, filename=f"達我做的{style_cfg['name']}_{bars}小節_{bpm}bpm.mid")
        embed = discord.Embed(
            title=f"🎼 小達痛得要死的編曲{style_cfg['name']}！",
            description=f"主奏樂器：**{display_name}**\n"
                        f"伴奏規格：**手收會有點小，痛，優~**\n"
                        f"樂曲總長：**{bars} 小節** **{bpm} BPM** 🎵",
            color=COLOR_TURTLE
        )
        await interaction.followup.send(embed=embed, file=discord_file)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

bot.tree.add_command(midi_group)


# =========================================================
# 4. DEV 分類指令群組：/dev [...] (開發者與管理專用)
# =========================================================
dev_group = app_commands.Group(name="dev", description="開發者專用指令群組")

@dev_group.command(name='restart', description='重新啟動小達機器人 (作者專用)')
async def dev_restart(interaction: discord.Interaction):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if interaction.user.id not in DEVELOPER_IDS:
        embed = discord.Embed(
            title="⛔ 你不是達我主人",
            description="欸欸，這個只有達我的主人(爹)才能按喔！",
            color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    print(f"[{now}] 開發者 ID: {interaction.user.id} ({interaction.user}) 觸發了 [/dev restart]")
    
    embed = discord.Embed(
        title="🔄 機器人重啟中...",
        description="小達正在將系統重新啟動，請稍候片刻！",
        color=COLOR_TURTLE
    )
    await interaction.response.send_message(embed=embed)
    
    await bot.close()
    os.execv(sys.executable, ['python'] + sys.argv)

@dev_group.command(name='問題回報', description='向達我的主人回報系統 bug 或提交意見')
@app_commands.describe(content='請詳細說明您遇到的問題或回報內容')
@app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
async def report_issue(interaction: discord.Interaction, content: str):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = interaction.user
    
    # 私訊開發者的嚴格格式需求
    dm_text = f"{user.display_name}{user.id}|使用者id:{user.id}|回報內容為:[{content}]"

    success_count = 0
    for dev_id in DEVELOPER_IDS:
        try:
            dev_user = await bot.fetch_user(dev_id)
            if dev_user:
                await dev_user.send(dm_text)
                success_count += 1
        except Exception as e:
            print(f"無法發送私訊給達我的主人 {dev_id}: {e}")

    if success_count > 0:
        embed = discord.Embed(
            title="📨 回報轉**達**成功！",
            description="感謝你告訴答我！問題已經告訴達我的主人了！就看他有沒有空處理:)",
            color=COLOR_TURTLE
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="🚨 轉達失敗",
            description="暫時無法轉達給達我的主人，請稍後再試！",
            color=COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

bot.tree.add_command(dev_group)


# =========================================================
# 5. TEST 分類指令群組：/test [...]
# =========================================================
test_group = app_commands.Group(name="test", description="系統測試與軟體狀態指令群組")

@test_group.command(name='ping', description='看看小達腦袋延遲')
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def ping(interaction: discord.Interaction):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 使用者ID: {interaction.user.id} ({interaction.user}) 使用了指令 [/test ping]")

    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 乒乓球時間！",
        description=f"達我愛打乒乓球！達我的延遲時間是 **{latency} ms**！",
        color=COLOR_TURTLE
    )
    await interaction.response.send_message(embed=embed)

bot.tree.add_command(test_group)
# ╭────────────────────────╮
# │看甚麼看！達我正在休息>:( │
# ╰────────────────╲───────╯
#   ___________     ╲⎠
#  /            \                               
# |         ⊖   |       ╱⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺╲    ⎫
# |___________   |     ╱                    ╲    
#      |          \  ╱                  ⎺⎺⎺⎺⎺⎺⎺⎠⎺⎺⎺⎺⎺⎺ ▹
#    ⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺ ⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺   ⎛              ⎠▹

# 啟動機器人 (從環境變數讀取 DISCORD_TOKEN)
TOKEN = os.getenv('DISCORD_TOKEN')

if __name__ == '__main__':
    if not TOKEN:
        print("🚨 錯誤：未能在環境變數中找到 DISCORD_TOKEN！請在託管平台設定。")
    else:
        bot.run(TOKEN)
