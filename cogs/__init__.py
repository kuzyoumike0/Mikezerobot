# cogs/__init__.py

# 1. パッケージ内のサブモジュール（Cog）をimport
from .helpme import HelpMe
from .setupvc import SetupVC
from .vote import Vote
from .creategroup import CreateGroup
from .vctimer import VCTimer
from .join_sound import JoinSound
from .setup_secret import SetupSecret
from .server_pet_cog_buttons import ServerPetCogButtons

# 2. __all__ に公開したい名前を列挙（from cogs import * で読み込まれる）
__all__ = [
    "HelpMe",
    "SetupVC",
    "Vote",
    "CreateGroup",
    "VCTimer",
    "JoinSound",
    "SetupSecret",
    "ServerPetCogButtons"
]

# 3. パッケージの初期化処理（必要に応じて）
# 例: パッケージ読み込み時にログを出すなど
print("cogsパッケージが読み込まれました")
