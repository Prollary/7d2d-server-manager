"""七日杀服务器常见崩溃/错误模式知识库"""

CRASH_PATTERNS = [
    {
        "id": "oom",
        "keywords": ["OutOfMemoryException", "out of memory", "insufficient memory"],
        "level": "critical",
        "cause": "服务器内存不足 (OutOfMemoryException)",
        "solution": (
            "1. 将服务器物理内存增至 8GB 以上（推荐 16GB）\n"
            "2. 在【服务器设置】中降低 MaxSpawnedZombies（推荐 40-60）\n"
            "3. 降低 ServerMaxPlayerCount 减少同时在线玩家数\n"
            "4. 设置定时重启任务（如每 12 小时）释放内存积累"
        ),
    },
    {
        "id": "null_ref",
        "keywords": ["NullReferenceException", "Object reference not set"],
        "level": "error",
        "cause": "对象空引用异常，常由模组冲突或存档数据损坏引起",
        "solution": (
            "1. 先在【模组管理】中禁用所有模组，测试是否还会崩溃\n"
            "2. 若禁用模组后正常，逐个启用模组定位冲突模组\n"
            "3. 若无模组，尝试删除玩家存档（Saves/Players 目录）\n"
            "4. 升级模组至支持当前游戏版本的最新版"
        ),
    },
    {
        "id": "port_conflict",
        "keywords": [
            "address already in use",
            "Only one usage of each socket address",
            "SocketException",
            "bind failed",
        ],
        "level": "error",
        "cause": "端口被其他程序占用，服务器无法绑定网络端口",
        "solution": (
            "1. 在【辅助工具 > 网络诊断】中检查端口占用情况\n"
            "2. 在 serverconfig.xml 中将 ServerPort 改为其他可用端口（如 26902）\n"
            "3. 确认防火墙规则已开放 TCP 和 UDP 端口\n"
            "4. 检查是否有残留的服务器进程（使用【强制终止】按钮）"
        ),
    },
    {
        "id": "steam_auth",
        "keywords": ["Steam authentication failed", "Steam ticket", "VAC", "EAC"],
        "level": "warning",
        "cause": "Steam/EAC 验证失败，玩家无法进入服务器",
        "solution": (
            "1. 检查服务器网络与 Steam 服务器的连通性\n"
            "2. 临时关闭 EAC：在 serverconfig.xml 中设置 EACEnabled=false（仅测试用）\n"
            "3. 运行【一键下载/更新服务端】确保 EAC 文件完整\n"
            "4. 参考：七日杀贴吧 - EAC 验证失败解决方案"
        ),
    },
    {
        "id": "disk_full",
        "keywords": ["disk full", "no space left", "IOException", "there is not enough space"],
        "level": "critical",
        "cause": "磁盘空间不足，服务器无法写入日志或存档文件",
        "solution": (
            "1. 立即清理磁盘，至少保留 10GB 可用空间\n"
            "2. 清理旧日志文件（output_log.txt 可能已达数 GB）\n"
            "3. 在【地图管理】中删除不需要的旧地图\n"
            "4. 考虑将存档目录迁移到更大容量的磁盘"
        ),
    },
    {
        "id": "database_error",
        "keywords": ["SQLiteException", "database is locked", "unable to open database", "database disk image is malformed"],
        "level": "error",
        "cause": "游戏数据库（SQLite）损坏或被锁定",
        "solution": (
            "1. 停止服务器后，使用【地图管理 > 一键备份】备份当前存档\n"
            "2. 从近期备份还原存档（使用回档功能）\n"
            "3. 删除损坏玩家的数据文件（Saves/Players/ 目录下对应玩家文件）\n"
            "4. 尝试删除 DynamicMeshManager.dat 文件后重启"
        ),
    },
    {
        "id": "xml_parse",
        "keywords": ["XmlException", "XML parse error", "ParseError", "xml error", "not well-formed"],
        "level": "error",
        "cause": "配置文件（XML）格式错误，服务器无法解析 serverconfig.xml",
        "solution": (
            "1. 使用【服务器设置】可视化编辑器修改配置，避免手动改 XML\n"
            "2. 检查 serverconfig.xml 中是否有中文路径或特殊字符\n"
            "3. 从原始 serverconfig.xml 模板重新配置\n"
            "4. 路径中不要包含空格或中文字符"
        ),
    },
    {
        "id": "mod_error",
        "keywords": ["ModInfo.xml", "Could not load mod", "mod loading failed", "Harmony", "Patch"],
        "level": "error",
        "cause": "模组加载失败，可能与当前游戏版本不兼容",
        "solution": (
            "1. 在【模组管理】中禁用所有模组后重启服务器\n"
            "2. 在七日杀贴吧或熊天琪论坛确认模组是否支持当前版本\n"
            "3. 下载模组最新版本重新安装\n"
            "4. 注意：Alpha 版本更新后大多数模组需要等待作者更新"
        ),
    },
    {
        "id": "blood_moon",
        "keywords": ["blood moon crash", "zombie horde", "BloodMoon", "horde night"],
        "level": "warning",
        "cause": "血月/尸潮期间崩溃，可能因僵尸数量过多耗尽服务器资源",
        "solution": (
            "1. 在【服务器设置】中降低 BloodMoonEnemyCount（推荐 16-32）\n"
            "2. 降低 MaxSpawnedZombies（推荐 40-60）\n"
            "3. 血月期间减少同时在线玩家数量\n"
            "4. 将服务器内存升级至 16GB\n"
            "5. 参考：熊天琪论坛 - 服务器性能优化指南"
        ),
    },
    {
        "id": "version_mismatch",
        "keywords": ["version mismatch", "Protocol version", "incompatible version", "client version"],
        "level": "warning",
        "cause": "客户端与服务端版本不匹配，玩家无法连接",
        "solution": (
            "1. 确保玩家游戏版本与服务端版本完全一致\n"
            "2. 使用【一键下载/更新服务端】更新服务端至最新版\n"
            "3. 玩家在 Steam 中右键游戏 > 属性 > 测试版，确认版本匹配\n"
            "4. 若需保持旧版：Steam 可选择指定游戏版本（Alpha XX）"
        ),
    },
    {
        "id": "telnet_fail",
        "keywords": ["Telnet refused", "TelnetEnabled", "connection refused 8081", "rcon"],
        "level": "warning",
        "cause": "Telnet/RCON 连接失败，无法执行远程管理命令",
        "solution": (
            "1. 在 serverconfig.xml 中确认 TelnetEnabled=true\n"
            "2. 检查 TelnetPort（默认 8081）防火墙规则\n"
            "3. 在【系统设置】中填入正确的 Telnet 密码\n"
            "4. 确认 TelnetPassword 已在 serverconfig.xml 中设置"
        ),
    },
    {
        "id": "saves_corrupt",
        "keywords": ["corrupt", "corrupted", "save data", "chunk error", "ChunkManager"],
        "level": "error",
        "cause": "存档数据损坏（ChunkManager 错误），可能因强制关闭服务器或磁盘错误引起",
        "solution": (
            "1. 立即停止服务器，使用回档功能恢复到最近的备份点\n"
            "2. 删除损坏的区块文件（.7dt / .7dt.bak 文件）\n"
            "3. 避免在服务器运行时强制断电或终止进程\n"
            "4. 定期使用【地图管理 > 一键备份】功能保存存档\n"
            "5. 参考：七日杀贴吧 - 存档修复教程"
        ),
    },
    {
        "id": "connection_timeout",
        "keywords": ["connection timed out", "timeout", "kicked: timeout", "ping timeout"],
        "level": "warning",
        "cause": "玩家连接超时被踢出，可能因服务器延迟过高或网络问题",
        "solution": (
            "1. 检查服务器带宽是否充足（推荐上行 10Mbps 以上/每玩家）\n"
            "2. 在 serverconfig.xml 中适当提高 ServerMaxPlayerCount 的网络限制\n"
            "3. 检查服务器 CPU/内存使用率，降低 MaxSpawnedZombies\n"
            "4. 建议服务器与玩家部署在同一地区以降低延迟"
        ),
    },
]
