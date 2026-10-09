# Bus Scene 素材与运行模块

独立于原有 BBQ、切菜、烧烤素材。当前固定画布 1280×720，车内参照画布 1056×442，所有事件均完整帧播放。

- backgrounds/bus-scene/waiting_bus：PASAR 站台、黄色巴士、向下箭头及主角站位配置。
- backgrounds/bus-scene/animations：idle、面具、拐杖、偷吃、放屁；每组 48 帧，以及固定 grid / 布局记录。
- backgrounds/bus-scene/in_bus：车厢背景与旧底图。
- characters/bus-scene：按主角、司机、小孩、老奶奶、上班族、肥宅分类的角色动画。
- ui/bus-scene：生命面包、食材卡、警告、菜单等像素素材。地图图标不再显示。
- audio/bus-scene/bgm：当前竞速音乐；audio/bus-scene/sfx：事件拟声、脚步、跳跃、到站喇叭。
- sprites/bus-scene/transitions：巴士幕布转场。
- sprites/bus-scene/effects：食材散落、FAILED、道具等通用效果和旧版参考。
- backgrounds/bus-scene/destination：到站转场显示的原项目背景。
Python 运行模块及自带 pygame-ce 已移到 game/bus_runtime，assets 中仅保留素材。
- asset-index.json：原始路径到分类路径的对照。

操作：A/D 移动，空格跳跃；走到巴士旁按 Enter 上车，箭头上方显示像素 ENTER。面具 J、拐杖 K、偷吃 L、放屁 I；每次按下后松开再按。圈外连续满 5 秒扣一格生命值，返回立即清零；暂停不计时。

从 TheFamilyNight-ISE 项目目录执行 `py -3.12 main.py --windowed`。不使用 BAT。成功到站仍自动进入原 BBQ 场景。
