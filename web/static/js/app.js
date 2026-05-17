const { createApp, ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } = Vue;

// axios 实例（稍后注入 token）
const api = axios.create({ baseURL: '/' });

// Token 只存内存，刷新页面即失效（强制重新登录）

// ── 地区选项 ──
const REGION_OPTIONS = [
  { value: 'Asia',                   label: '亚洲（Asia）' },
  { value: 'Middle East',            label: '中东（Middle East）' },
  { value: 'Africa',                 label: '非洲（Africa）' },
  { value: 'Oceania',                label: '大洋洲（Oceania）' },
  { value: 'North America - East',   label: '北美 – 东部（NA East）' },
  { value: 'North America - West',   label: '北美 – 西部（NA West）' },
  { value: 'Central America',        label: '中美洲（Central America）' },
  { value: 'South America',          label: '南美洲（South America）' },
  { value: 'Europe',                 label: '欧洲（Europe）' },
  { value: 'Russia',                 label: '俄罗斯（Russia）' },
];

createApp({
  setup() {

    // ══════════════════════════════════════════
    //  应用状态：loading | auth | app
    // ══════════════════════════════════════════
    const appState   = ref('loading'); // loading | auth | app
    const authMode   = ref('login');   // login | register
    const authUser   = ref('');
    const authPass   = ref('');
    const authError  = ref('');
    const authBusy   = ref(false);
    const currentUser= ref('');
    const authToken  = ref('');
    const usersFile  = ref('');

    function setToken(token, username) {
      // 仅保存在内存，不写 localStorage — 刷新页面即失效
      authToken.value = token;
      currentUser.value = username;
      api.defaults.headers.common['X-Auth-Token'] = token;
    }

    function clearToken() {
      authToken.value = '';
      currentUser.value = '';
      delete api.defaults.headers.common['X-Auth-Token'];
    }

    async function checkAuth() {
      // 每次页面加载均直接显示登录框，不自动恢复 session
      appState.value = 'auth';
    }

    async function doAuth() {
      authError.value = '';
      authBusy.value  = true;
      try {
        const body = { username: authUser.value.trim(), password: authPass.value };
        const url  = authMode.value === 'login' ? '/api/auth/login' : '/api/auth/register';
        const { data } = await axios.post(url, body);
        setToken(data.token, data.username);
        appState.value = 'app';
        onAppReady();
      } catch (e) {
        authError.value = e.response?.data?.detail || '操作失败，请重试';
      } finally {
        authBusy.value = false;
      }
    }

    async function logout() {
      try { await api.post(`/api/auth/logout?token=${authToken.value}`); } catch {}
      clearToken();
      appState.value = 'auth';
      authUser.value = '';
      authPass.value = '';
    }

    async function fetchUsersFile() {
      try {
        const { data } = await api.get('/api/auth/info');
        usersFile.value = data.users_file || '';
      } catch {}
    }

    // ══════════════════════════════════════════
    //  导航
    // ══════════════════════════════════════════
    const page = ref('dashboard');
    const sidebarOpen = ref(false);

    // 移动端底部导航快捷项
    const bottomTabs = [
      { id: 'dashboard', icon: '⬛', label: '控制台' },
      { id: 'players',   icon: '👥', label: '玩家' },
      { id: 'worlds',    icon: '🗺',  label: '地图' },
      { id: 'mods',      icon: '🔧', label: '模组' },
      { id: 'sysconfig', icon: '🔩', label: '设置' },
    ];

    const navGroups = [
      {
        label: '服务管理',
        items: [
          { id: 'dashboard', label: '服务器控制台', icon: '⬛' },
          { id: 'players',   label: '玩家管理',     icon: '👥' },
        ],
      },
      {
        label: '内容管理',
        items: [
          { id: 'mods',   label: '模组管理', icon: '🔧' },
          { id: 'worlds', label: '地图管理', icon: '🗺' },
        ],
      },
      {
        label: '配置',
        items: [
          { id: 'settings',  label: '服务器设置', icon: '⚙' },
          { id: 'tools',     label: '辅助工具',   icon: '🛠' },
          { id: 'sysconfig', label: '系统设置',   icon: '🔩' },
        ],
      },
    ];

    function switchPage(p) {
      page.value = p;
      sidebarOpen.value = false;
      ctxMenu.show = false;
      if (p === 'players')  fetchPlayers();
      if (p === 'mods')     fetchMods();
      if (p === 'worlds')   fetchWorlds();
      if (p === 'settings') fetchServerConfig();
      if (p === 'sysconfig'){ fetchSysPaths(); fetchUsersFile(); }
      if (p === 'dashboard') fetchSnapshots();
    }

    // ══════════════════════════════════════════
    //  Toast
    // ══════════════════════════════════════════
    const toasts = ref([]);
    function toast(msg, type = 'info') {
      const id = Date.now() + Math.random();
      toasts.value.push({ id, msg, type });
      setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id); }, 3800);
    }

    // ══════════════════════════════════════════
    //  页面弹窗
    // ══════════════════════════════════════════
    const modal = reactive({
      show: false, title: '', icon: '', content: '', type: 'info',
      onConfirm: null, confirmText: '确定', cancelText: '取消', confirmClass: 'btn-primary',
    });

    function closeModal() {
      if (modal._reject) modal._reject();
      modal.show = false;
    }
    function confirmModal() {
      if (modal.onConfirm) modal.onConfirm();
      modal.show = false;
    }
    function askConfirm(title, content, confirmText = '确定', confirmClass = 'btn-red') {
      return new Promise(resolve => {
        Object.assign(modal, {
          show: true, title, content, icon: '⚠', type: 'confirm',
          confirmText, cancelText: '取消', confirmClass,
          onConfirm: () => resolve(true),
          _reject:   () => resolve(false),
        });
      });
    }

    // ══════════════════════════════════════════
    //  服务器状态
    // ══════════════════════════════════════════
    const serverRunning = ref(false);
    const serverPid     = ref(null);
    const statusLoading = ref(false);

    async function fetchStatus() {
      try {
        const { data } = await api.get('/api/server/status');
        serverRunning.value = data.running;
        serverPid.value = data.pid;
      } catch {}
    }

    async function startServer() {
      statusLoading.value = true;
      try { const { data } = await api.post('/api/server/start'); toast(data.message, data.success ? 'success' : 'error'); }
      catch (e) { toast(e.response?.data?.detail || '请求失败', 'error'); }
      finally { statusLoading.value = false; await fetchStatus(); }
    }

    async function stopServer() {
      const ok = await askConfirm('停止服务器', '确认正常关闭服务器？若30秒内未响应请使用强制终止。', '停止', 'btn-orange');
      if (!ok) return;
      statusLoading.value = true;
      try { const { data } = await api.post('/api/server/stop'); toast(data.message, data.success ? 'info' : 'error'); }
      catch (e) { toast(e.response?.data?.detail || '请求失败', 'error'); }
      finally { statusLoading.value = false; }
    }

    async function forceStop() {
      const ok = await askConfirm('强制终止', '强制终止可能导致存档损坏，确认继续？', '强制终止', 'btn-red');
      if (!ok) return;
      try { const { data } = await api.post('/api/server/force-stop'); toast(data.message, 'info'); await fetchStatus(); }
      catch (e) { toast(e.response?.data?.detail || '请求失败', 'error'); }
    }

    async function restartServer() {
      const ok = await askConfirm('重启服务器', '确认重启服务器？', '重启', 'btn-orange');
      if (!ok) return;
      try { const { data } = await api.post('/api/server/restart'); toast(data.message, 'info'); }
      catch (e) { toast(e.response?.data?.detail || '请求失败', 'error'); }
    }

    // ══════════════════════════════════════════
    //  SSE 日志
    // ══════════════════════════════════════════
    const logs  = ref([]);
    const logEl = ref(null);
    let _es = null;

    function colorClass(line) {
      const l = line.toLowerCase();
      if (l.includes('err') || l.includes('exception') || l.includes('fatal')) return 'log-err';
      if (l.includes('wrn') || l.includes('warning'))  return 'log-warn';
      if (l.includes('[steamcmd]'))                     return 'log-steamcmd';
      if (l.includes('inf') || l.includes('[*]'))       return 'log-info';
      if (l.includes('──') || l.includes('[cmd]'))      return 'log-sys';
      return '';
    }

    function connectSSE() {
      if (_es) _es.close();
      const token = authToken.value;
      _es = new EventSource(`/api/server/stream?token=${token}`);
      _es.onmessage = (e) => {
        if (!e.data) return;
        const atBottom = !logEl.value || logEl.value.scrollTop + logEl.value.clientHeight >= logEl.value.scrollHeight - 40;
        logs.value.push(e.data);
        if (logs.value.length > 2000) logs.value.splice(0, logs.value.length - 2000);
        if (atBottom) nextTick(() => { if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight; });
      };
      _es.onerror = () => { _es.close(); setTimeout(connectSSE, 3000); };
    }

    function clearLogs() { logs.value = []; }

    // ══════════════════════════════════════════
    //  控制台指令
    // ══════════════════════════════════════════
    const cmdInput   = ref('');
    const cmdLoading = ref(false);
    const cmdHistory = [];
    let _histIdx = -1;

    async function sendCommand() {
      const cmd = cmdInput.value.trim();
      if (!cmd) return;
      cmdHistory.unshift(cmd); if (cmdHistory.length > 50) cmdHistory.pop();
      _histIdx = -1; cmdInput.value = ''; cmdLoading.value = true;
      try {
        const { data } = await api.post('/api/server/command', { command: cmd });
        if (data.output) {
          data.output.split('\n').forEach(l => { if (l.trim()) logs.value.push('[CMD] ' + l); });
          nextTick(() => { if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight; });
        }
      } catch (e) { toast(e.response?.data?.detail || '指令发送失败', 'error'); }
      finally { cmdLoading.value = false; }
    }

    function onCmdKeydown(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendCommand(); }
      if (e.key === 'ArrowUp')   { _histIdx = Math.min(_histIdx + 1, cmdHistory.length - 1); cmdInput.value = cmdHistory[_histIdx] || ''; }
      if (e.key === 'ArrowDown') { _histIdx = Math.max(_histIdx - 1, -1); cmdInput.value = _histIdx >= 0 ? cmdHistory[_histIdx] : ''; }
    }

    // ══════════════════════════════════════════
    //  崩溃检测
    // ══════════════════════════════════════════
    const crashModal = reactive({ show: false, loading: false, found: false, issues: [], message: '' });

    async function detectCrash() {
      crashModal.show = true; crashModal.loading = true; crashModal.issues = []; crashModal.found = false;
      try {
        const { data } = await api.get('/api/server/crash');
        crashModal.found = data.found;
        crashModal.issues = data.issues || [];
        crashModal.message = data.message || '';
      } catch (e) { crashModal.message = '检测失败：' + (e.response?.data?.detail || e.message); }
      finally { crashModal.loading = false; }
    }

    // ══════════════════════════════════════════
    //  回档
    // ══════════════════════════════════════════
    const snapshots = ref({});
    const ROLLBACK_LABELS = { '5min':'5分钟', '30min':'30分钟', '3h':'3小时', 'daily':'昨日凌晨' };

    async function fetchSnapshots() {
      try { const { data } = await api.get('/api/server/snapshots'); snapshots.value = data.snapshots || {}; } catch {}
    }

    async function doRollback(tag) {
      const snap = snapshots.value[tag];
      const info = snap ? `快照：${snap.replace(/snap_\w+_/, '').replace('.zip', '')}` : '暂无快照';
      const ok = await askConfirm(`回档至 ${ROLLBACK_LABELS[tag]}`, `回档前将自动备份当前存档。${info}\n\n请确保服务器已停止后再执行回档。`, `确认回档`, 'btn-orange');
      if (!ok) return;
      try {
        const { data } = await api.post('/api/server/rollback', { tag });
        toast(data.message, data.success ? 'success' : 'error');
        if (data.success) fetchSnapshots();
      } catch (e) { toast(e.response?.data?.detail || '回档失败', 'error'); }
    }

    // ══════════════════════════════════════════
    //  玩家管理
    // ══════════════════════════════════════════
    const players  = ref([]);
    const playersLoading = ref(false);
    const ctxMenu  = reactive({ show: false, x: 0, y: 0, player: null });

    async function fetchPlayers() {
      playersLoading.value = true;
      try { const { data } = await api.get('/api/server/players'); players.value = data.players || []; }
      catch (e) { toast(e.response?.data?.detail || '获取玩家列表失败', 'error'); }
      finally { playersLoading.value = false; }
    }

    function showCtxMenu(e, player) { e.preventDefault(); ctxMenu.show = true; ctxMenu.x = e.clientX; ctxMenu.y = e.clientY; ctxMenu.player = player; }
    function hideCtxMenu() { ctxMenu.show = false; }

    async function execPlayerAction(action) {
      hideCtxMenu();
      const p = ctxMenu.player; if (!p) return;
      const labels = { kick:'踢出', ban:'封禁', admin:'设管理员', unadmin:'撤销管理员', unban:'解封' };
      let reason = '', duration = 'perm';
      if (action === 'kick' || action === 'ban') { reason = window.prompt(`对玩家 "${p.name}" 的${labels[action]}原因（可留空）:`) ?? ''; if (reason === null) return; }
      if (action === 'ban') { const dur = window.prompt('封禁时长（如：60 minutes / 7 days / perm）', 'perm'); if (dur === null) return; duration = dur || 'perm'; }
      const ok = await askConfirm(`确认${labels[action]}`, `对玩家 "${p.name}" 执行【${labels[action]}】？`, labels[action], action === 'ban' ? 'btn-red' : 'btn-orange');
      if (!ok) return;
      try {
        const { data } = await api.post('/api/server/players/action', { player_id: p.id, action, reason, duration });
        toast(data.message, 'success');
        if (action === 'kick' || action === 'ban') await fetchPlayers();
      } catch (e) { toast(e.response?.data?.detail || '操作失败', 'error'); }
    }

    // ══════════════════════════════════════════
    //  模组管理
    // ══════════════════════════════════════════
    const mods = ref([]);
    async function fetchMods() {
      try { const { data } = await api.get('/api/mods'); mods.value = data.mods; } catch (e) { toast(e.response?.data?.detail || '加载模组失败', 'error'); }
    }
    async function uploadMod(e) {
      const file = e.target.files[0]; if (!file) return;
      const fd = new FormData(); fd.append('file', file);
      try { const { data } = await api.post('/api/mods/upload', fd); toast(data.message, 'success'); await fetchMods(); }
      catch (e) { toast(e.response?.data?.detail || '上传失败', 'error'); }
      e.target.value = '';
    }
    async function toggleMod(raw) {
      try { await api.put(`/api/mods/${encodeURIComponent(raw)}/toggle`); await fetchMods(); } catch (e) { toast(e.response?.data?.detail || '操作失败', 'error'); }
    }
    async function deleteMod(raw, name) {
      const ok = await askConfirm('删除模组', `确认删除模组 "${name}"？`, '删除', 'btn-red'); if (!ok) return;
      try { await api.delete(`/api/mods/${encodeURIComponent(raw)}`); toast(`已删除 "${name}"`, 'success'); await fetchMods(); } catch (e) { toast(e.response?.data?.detail || '删除失败', 'error'); }
    }

    // ══════════════════════════════════════════
    //  地图管理
    // ══════════════════════════════════════════
    const worlds = ref([]); const currentWorld = ref(''); const selectedWorld = ref('');
    async function fetchWorlds() {
      try { const { data } = await api.get('/api/worlds'); worlds.value = data.worlds; currentWorld.value = data.current; selectedWorld.value = data.current; } catch (e) { toast(e.response?.data?.detail || '加载地图失败', 'error'); }
    }
    async function uploadWorld(e) {
      const file = e.target.files[0]; if (!file) return;
      const fd = new FormData(); fd.append('file', file);
      try { const { data } = await api.post('/api/worlds/upload', fd); toast(data.message, 'success'); await fetchWorlds(); } catch (e) { toast(e.response?.data?.detail || '上传失败', 'error'); }
      e.target.value = '';
    }
    async function switchWorld() {
      if (!selectedWorld.value) return;
      try { const { data } = await api.put('/api/worlds/switch', { world_name: selectedWorld.value }); toast(data.message, 'success'); await fetchWorlds(); } catch (e) { toast(e.response?.data?.detail || '切换失败', 'error'); }
    }
    async function deleteWorld(name) {
      const ok = await askConfirm('删除地图', `确认删除 "${name}"？`, '删除', 'btn-red'); if (!ok) return;
      try { await api.delete(`/api/worlds/${encodeURIComponent(name)}`); toast(`已删除 "${name}"`, 'success'); await fetchWorlds(); } catch (e) { toast(e.response?.data?.detail || '删除失败', 'error'); }
    }
    function backupWorld() {
      const a = document.createElement('a');
      a.href = `/api/worlds/backup?token=${authToken.value}`;
      a.download = ''; document.body.appendChild(a); a.click(); document.body.removeChild(a);
      toast('存档备份下载已开始', 'success');
    }

    // ══════════════════════════════════════════
    //  服务器设置
    // ══════════════════════════════════════════
    const serverConfig = ref({});
    const hanizeLoading = ref(false);

    const FIELD_DEFS = [
      { key: 'ServerName',           label: '服务器名称',         type: 'text' },
      { key: 'ServerDescription',    label: '服务器描述',         type: 'text' },
      { key: 'ServerVisibility',     label: '服务器可见性',       type: 'select', options: ['0','1','2'], labels: ['未列出','仅朋友','公用'] },
      { key: 'ServerPassword',       label: '服务器密码',         type: 'text' },
      { key: 'ServerMaxPlayerCount', label: '最大玩家数',         type: 'number', min: 1, max: 64 },
      { key: 'GameDifficulty',       label: '游戏难度',           type: 'select', options: ['0','1','2','3','4','5'], labels: ['最简单','简单','普通','困难','非常困难','最难'] },
      { key: 'ZombieMove',           label: '僵尸速度（白天）',   type: 'select', options: ['0','1','2','3'], labels: ['缓行','慢跑','奔跑','冲刺'] },
      { key: 'ZombieMoveNight',      label: '僵尸速度（夜晚）',   type: 'select', options: ['0','1','2','3'], labels: ['缓行','慢跑','奔跑','冲刺'] },
      { key: 'BloodMoonFrequency',   label: '血月频率（天）',     type: 'number', min: 0, max: 99 },
      { key: 'BloodMoonEnemyCount',  label: '血月僵尸数',         type: 'number', min: 8, max: 128 },
      { key: 'MaxSpawnedZombies',    label: '最大僵尸生成数',     type: 'number', min: 1, max: 200 },
      { key: 'XPMultiplier',         label: '经验倍率（%）',      type: 'number', min: 1, max: 500 },
      { key: 'LootAbundance',        label: '战利品丰富度（%）',  type: 'number', min: 0, max: 500 },
      { key: 'LootRespawnDays',      label: '战利品重置天数',     type: 'number', min: 0, max: 999 },
      { key: 'DropOnDeath',          label: '死亡掉落',           type: 'select', options: ['0','1','2','3'], labels: ['不掉落','删除背包','掉落所有','掉落装备'] },
      { key: 'PlayerKillingMode',    label: 'PVP 模式',           type: 'select', options: ['0','1','2','3'], labels: ['禁止PVP','只能打非队友','只能打非盟友','可打任何人'] },
      { key: 'AirDropFrequency',     label: '空投频率(小时)',     type: 'number', min: 0, max: 999 },
      { key: 'AirDropMarker',        label: '空投标记',           type: 'bool' },
      { key: 'LandClaimCount',       label: '领地石数量',         type: 'number', min: 1, max: 10 },
      { key: 'LandClaimSize',        label: '领地石尺寸',         type: 'number', min: 1, max: 100 },
      { key: 'LandClaimDeadZone',    label: '领地石安全间距',     type: 'number', min: 0, max: 100 },
      { key: 'LandClaimExpiryTime',  label: '领地有效时间(天)',   type: 'number', min: 0, max: 100 },
      { key: 'LandClaimDecayMode',   label: '领地石衰退模式',     type: 'select', options: ['0','1','2'], labels: ['线性(慢)','指数(快)','无'] },
      { key: 'LandClaimOnlineDurabilityModifier', label: '在线领地石硬度', type: 'number', min: 0, max: 100 },
      { key: 'LandClaimOfflineDurabilityModifier', label: '离线领地石硬度', type: 'number', min: 0, max: 100 },
      { key: 'LandClaimOfflineDelay', label: '离线生效延迟(分)', type: 'number', min: 0, max: 1440 },
      { key: 'EACEnabled',           label: '启用 EAC',           type: 'bool' },
      { key: 'TelnetEnabled',        label: '启用 Telnet',        type: 'bool' },
      { key: 'TelnetPort',           label: 'Telnet 端口',        type: 'number', min: 1, max: 65535 },
      { key: 'TelnetPassword',       label: 'Telnet 密码',        type: 'text' },
      { key: 'ServerPort',           label: '服务器端口',         type: 'number', min: 1, max: 65535 },
      { key: 'Region',               label: '地区',               type: 'region' },
    ];

    async function fetchServerConfig() {
      try { const { data } = await api.get('/api/config/server'); serverConfig.value = { ...data.properties }; }
      catch (e) { toast(e.response?.data?.detail || '加载配置失败', 'error'); }
    }
    async function saveServerConfig() {
      try { const { data } = await api.post('/api/config/server', serverConfig.value); toast(data.message, 'success'); }
      catch (e) { toast(e.response?.data?.detail || '保存失败', 'error'); }
    }
    async function hanizeConfig() {
      const ok = await askConfirm('一键汉化配置', '将为 serverconfig.xml 添加中文注释，操作前自动备份。确认？', '汉化', 'btn-blue'); if (!ok) return;
      hanizeLoading.value = true;
      try { const { data } = await api.post('/api/config/hanize'); toast(data.message, 'success'); }
      catch (e) { toast(e.response?.data?.detail || '汉化失败', 'error'); }
      finally { hanizeLoading.value = false; }
    }

    // ══════════════════════════════════════════
    //  辅助工具
    // ══════════════════════════════════════════
    const portResults = ref({}); const fwResults = ref({});
    async function checkPorts() { try { const { data } = await api.get('/api/tools/network'); portResults.value = data.ports; } catch { toast('端口检查失败', 'error'); } }
    async function openFirewall() { try { const { data } = await api.post('/api/tools/firewall'); fwResults.value = data.results; toast('防火墙规则已处理', 'info'); } catch { toast('操作失败（需管理员权限）', 'error'); } }

    // ══════════════════════════════════════════
    //  系统设置
    // ══════════════════════════════════════════
    const sysPaths = reactive({ server_dir: '', config_path: '', web_host: '0.0.0.0', web_port: 8888 });
    const autoSearching = ref(false);

    async function fetchSysPaths() { try { const { data } = await api.get('/api/config/paths'); Object.assign(sysPaths, data); } catch {} }
    async function saveSysPaths() {
      try { const { data } = await api.post('/api/config/paths', { server_dir: sysPaths.server_dir, config_path: sysPaths.config_path, web_host: sysPaths.web_host, web_port: sysPaths.web_port }); toast(data.message, 'success'); }
      catch (e) { toast(e.response?.data?.detail || '保存失败', 'error'); }
    }
    async function autoSearch() {
      autoSearching.value = true;
      try { const { data } = await api.get('/api/config/auto-search'); if (data.success) { sysPaths.server_dir = data.server_dir; sysPaths.config_path = data.config_path; toast(data.message, 'success'); } else { toast(data.message, 'warn'); } }
      catch { toast('自动搜索失败', 'error'); }
      finally { autoSearching.value = false; }
    }
    async function installServer() {
      const ok = await askConfirm('下载服务端', '将使用 SteamCMD 自动下载七日杀服务端（数十GB），下载过程可在控制台查看。确认继续？', '开始下载', 'btn-blue'); if (!ok) return;
      try { const { data } = await api.post('/api/server/install', {}); toast(data.message, data.success ? 'success' : 'error'); if (data.success) switchPage('dashboard'); }
      catch (e) { toast(e.response?.data?.detail || '请求失败', 'error'); }
    }

    // ══════════════════════════════════════════
    //  初始化
    // ══════════════════════════════════════════
    function onAppReady() {
      fetchStatus();
      fetchSnapshots();
      connectSSE();
      statusInterval = setInterval(fetchStatus, 5000);
    }

    let statusInterval;
    onMounted(async () => {
      document.addEventListener('click', hideCtxMenu);
      await checkAuth();
    });
    onUnmounted(() => {
      clearInterval(statusInterval);
      if (_es) _es.close();
      document.removeEventListener('click', hideCtxMenu);
    });

    return {
      // auth
      appState, authMode, authUser, authPass, authError, authBusy, currentUser, usersFile,
      doAuth, logout, fetchUsersFile,
      // nav
      page, navGroups, bottomTabs, sidebarOpen, switchPage,
      REGION_OPTIONS,
      // toast / modal
      toasts, modal, closeModal, confirmModal,
      // server
      serverRunning, serverPid, statusLoading,
      startServer, stopServer, forceStop, restartServer,
      // logs
      logs, logEl, colorClass, clearLogs,
      // cmd
      cmdInput, cmdLoading, sendCommand, onCmdKeydown,
      // crash
      crashModal, detectCrash,
      // rollback
      snapshots, ROLLBACK_LABELS, doRollback,
      // players
      players, playersLoading, ctxMenu, fetchPlayers, showCtxMenu, hideCtxMenu, execPlayerAction,
      // mods
      mods, fetchMods, uploadMod, toggleMod, deleteMod,
      // worlds
      worlds, currentWorld, selectedWorld, fetchWorlds, uploadWorld, switchWorld, deleteWorld, backupWorld,
      // settings
      serverConfig, FIELD_DEFS, fetchServerConfig, saveServerConfig, hanizeLoading, hanizeConfig,
      // tools
      portResults, fwResults, checkPorts, openFirewall,
      // sysconfig
      sysPaths, autoSearching, fetchSysPaths, saveSysPaths, autoSearch, installServer,
    };
  },

  template: `
<!-- ══ 加载中 ══════════════════════════════════════════════ -->
<div v-if="appState==='loading'" style="min-height:100vh;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:16px;background:var(--bg);">
  <div class="icon-7d2d icon-7d2d-md" style="animation:pulse 1.5s infinite;"><span class="i7">7</span><span class="drop"></span></div>
  <div style="color:var(--subtext);font-size:13px;letter-spacing:.5px;">七日杀联机平台 · 加载中…</div>
</div>

<!-- ══ 登录 / 注册 ══════════════════════════════════════════ -->
<div v-else-if="appState==='auth'" class="auth-page">
  <!-- 左上角装饰文字 -->
  <div class="auth-deco auth-deco-tl">☣ SURVIVAL MODE ACTIVE</div>
  <div class="auth-deco auth-deco-br">7 DAYS TO DIE · PLATFORM v2.0</div>

  <div class="auth-box">
    <div class="auth-logo">
      <div class="auth-logo-icon icon-7d2d icon-7d2d-lg"><span class="i7">7</span><span class="drop"></span></div>
      <div class="auth-logo-title">七日杀联机平台</div>
      <div class="auth-logo-sub">7 Days to Die · Server Manager</div>
    </div>

    <div class="auth-tabs">
      <button class="auth-tab" :class="{active:authMode==='login'}"    @click="authMode='login';authError=''">登录</button>
      <button class="auth-tab" :class="{active:authMode==='register'}" @click="authMode='register';authError=''">注册</button>
    </div>

    <div v-if="authError" class="auth-error">{{ authError }}</div>

    <div class="auth-field">
      <label class="auth-label">用户名</label>
      <input class="auth-input" v-model="authUser" type="text" placeholder="输入用户名" autocomplete="username"
        @keydown.enter="doAuth" />
    </div>
    <div class="auth-field">
      <label class="auth-label">密码</label>
      <input class="auth-input" v-model="authPass" type="password" :placeholder="authMode==='register'?'至少6位':'输入密码'"
        autocomplete="current-password" @keydown.enter="doAuth" />
    </div>

    <button class="auth-submit" :disabled="authBusy" @click="doAuth">
      {{ authBusy ? '处理中…' : (authMode==='login' ? '登录' : '注册并登录') }}
    </button>

    <div class="auth-hint">
      忘记密码？删除服务器上的 <strong>users.json</strong> 文件后刷新页面重新注册。<br>
      （文件与 web_config.yaml 在同一目录）
    </div>
  </div>
</div>

<!-- ══ 主应用 ════════════════════════════════════════════════ -->
<div v-else-if="appState==='app'" class="app-shell" style="height:100vh;overflow:hidden;">

  <!-- 移动端顶部栏 -->
  <div class="topbar">
    <button class="topbar-btn" @click="sidebarOpen=!sidebarOpen">☰</button>
    <div class="topbar-brand">七日杀联机平台</div>
    <button class="topbar-btn" @click="logout" title="退出">⎋</button>
  </div>

  <!-- 移动端遮罩 -->
  <div class="sidebar-overlay" v-if="sidebarOpen" @click="sidebarOpen=false"></div>

  <!-- 侧边栏 -->
  <div id="sidebar" :class="{open:sidebarOpen}">
    <div class="sidebar-header">
      <div class="sidebar-brand">
        <div class="sidebar-brand-icon" style="background:none;box-shadow:none;border-radius:8px;overflow:hidden;">
          <img src="https://img.cdn1.vip/i/69fc6329c678f_1778148137.png" alt="7D2D" style="width:100%;height:100%;object-fit:contain;" />
        </div>
        <div>
          <div class="sidebar-brand-name">七日杀联机平台</div>
          <div class="sidebar-brand-sub">7D2D Server Manager</div>
        </div>
      </div>
      <div class="sidebar-user">
        <div class="sidebar-avatar">{{ currentUser ? currentUser[0].toUpperCase() : 'U' }}</div>
        <div class="sidebar-username">{{ currentUser }}</div>
        <button class="sidebar-logout" @click="logout" title="退出登录">✕</button>
      </div>
    </div>

    <nav class="sidebar-nav">
      <template v-for="g in navGroups" :key="g.label">
        <div class="nav-section-label">{{ g.label }}</div>
        <button v-for="item in g.items" :key="item.id"
          class="nav-btn" :class="{active: page===item.id}"
          @click="switchPage(item.id)">
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </button>
      </template>
    </nav>

    <!-- 侧边栏底部游戏插图 -->
    <div class="sidebar-art">
      <img src="https://img.cdn1.vip/i/69fc5ea8ec847_1778146984.webp" alt="" loading="lazy" />
    </div>

    <div class="sidebar-footer">
      <div class="sidebar-version">v2.0.0 · 七日杀联机平台</div>
    </div>
  </div>

  <!-- 主内容 -->
  <div id="main">

    <!-- ── 控制台 ── -->
    <div v-if="page==='dashboard'" class="page" style="overflow:hidden;padding-bottom:0;">
      <div class="page-header">
        <div class="page-title">服务器控制台</div>
        <div class="page-badge" :style="serverRunning?'background:rgba(25,214,140,.15);color:var(--green)':'background:rgba(255,79,94,.1);color:var(--red)'">
          {{ serverRunning ? '● 运行中' : '○ 已停止' }}
        </div>
      </div>

      <!-- 状态栏 -->
      <div class="status-bar">
        <div class="status-info">
          <div class="status-dot" :class="statusLoading?'loading':serverRunning?'on':'off'"></div>
          <div>
            <div class="status-label">{{ statusLoading?'处理中…':serverRunning?'服务器运行中':'服务器已停止' }}</div>
            <div v-if="serverPid" class="status-meta">PID {{ serverPid }}</div>
          </div>
        </div>
        <div class="btn-row">
          <button class="btn btn-green btn-sm"  :disabled="serverRunning||statusLoading"  @click="startServer">▶ 启动</button>
          <button class="btn btn-orange btn-sm" :disabled="!serverRunning||statusLoading" @click="stopServer">■ 停止</button>
          <button class="btn btn-orange btn-sm" :disabled="!serverRunning||statusLoading" @click="restartServer">↺ 重启</button>
          <button class="btn btn-ghost btn-sm"  :disabled="!serverRunning" @click="forceStop">⚡ 强制</button>
        </div>
      </div>

      <!-- 工具行 -->
      <div class="toolbar">
        <button class="btn btn-purple btn-sm" @click="detectCrash">🔍 AI崩溃检测</button>
        <span style="color:var(--subtext);font-size:12px;">回档：</span>
        <button v-for="(label,tag) in ROLLBACK_LABELS" :key="tag" class="btn btn-ghost btn-sm" @click="doRollback(tag)"
          :title="snapshots[tag]?'有备份':'暂无备份'">
          {{ label }}
          <span :style="snapshots[tag]?'color:var(--green)':'color:var(--muted)'">●</span>
        </button>
      </div>

      <!-- 日志 -->
      <div class="console-wrap" style="flex:1;min-height:0;margin-bottom:24px;">
        <div class="console-toolbar">
          <div class="console-dots"><span class="console-dot console-dot-r"></span><span class="console-dot console-dot-y"></span><span class="console-dot console-dot-g"></span></div>
          <span class="console-title">实时日志</span>
          <button class="btn btn-ghost btn-xs" @click="clearLogs">清空</button>
        </div>
        <div class="log-console" ref="logEl">
          <div v-for="(line,i) in logs" :key="i" :class="colorClass(line)">{{ line }}</div>
          <span v-if="logs.length===0" style="color:var(--muted)">等待服务器输出…</span>
        </div>
        <div class="console-input-row">
          <input class="console-input" v-model="cmdInput" :disabled="!serverRunning||cmdLoading"
            placeholder="输入游戏指令（Enter 发送 · ↑↓ 历史记录）如：say Hello / weather 0 / lp"
            @keydown="onCmdKeydown" />
          <button class="btn btn-primary btn-sm" :disabled="!serverRunning||cmdLoading||!cmdInput.trim()" @click="sendCommand">
            {{ cmdLoading?'…':'发送' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── 玩家管理 ── -->
    <div v-if="page==='players'" class="page">
      <div class="page-header">
        <div class="page-title">在线玩家管理</div>
        <div class="page-badge">{{ players.length }} 人在线</div>
      </div>
      <div class="card">
        <div class="toolbar" style="margin-bottom:14px;">
          <button class="btn btn-blue btn-sm" @click="fetchPlayers" :disabled="playersLoading">{{ playersLoading?'加载中…':'刷新列表' }}</button>
          <span style="color:var(--subtext);font-size:12px;">右键玩家行执行操作</span>
        </div>
        <div v-if="!serverRunning" style="color:var(--yellow);font-size:13px;padding:8px 0;">⚠ 服务器未运行，启动并开启 Telnet 后刷新</div>
        <div v-else class="table-wrap">
          <table class="data-table" style="user-select:none;">
            <thead><tr><th>#</th><th>玩家名</th><th>Entity ID</th><th>IP</th><th>延迟</th></tr></thead>
            <tbody>
              <tr v-if="players.length===0&&!playersLoading"><td colspan="5" class="empty-tip">暂无在线玩家</td></tr>
              <tr v-for="(p,i) in players" :key="p.id" style="cursor:context-menu;" @contextmenu.prevent="showCtxMenu($event,p)">
                <td>{{ i+1 }}</td><td><strong>{{ p.name }}</strong></td>
                <td style="font-family:monospace;font-size:12px;">{{ p.id }}</td>
                <td>{{ p.ip||'-' }}</td>
                <td><span :style="{color:p.ping>150?'var(--red)':p.ping>80?'var(--yellow)':'var(--green)'}">{{ p.ping }}ms</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── 模组管理 ── -->
    <div v-if="page==='mods'" class="page">
      <div class="page-header"><div class="page-title">模组管理</div><div class="page-badge">{{ mods.length }} 个</div></div>
      <div class="card">
        <div class="toolbar" style="margin-bottom:14px;">
          <label class="btn btn-blue btn-sm" style="cursor:pointer;">+ 安装模组（ZIP）<input type="file" accept=".zip" style="display:none" @change="uploadMod"></label>
          <button class="btn btn-orange btn-sm" @click="fetchMods">🔍 扫描已有模组</button>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead><tr><th>模组名称</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-if="mods.length===0"><td colspan="3" class="empty-tip">暂无模组</td></tr>
              <tr v-for="m in mods" :key="m.raw">
                <td><strong>{{ m.name }}</strong></td>
                <td><span class="badge" :class="m.enabled?'badge-green':'badge-red'">{{ m.enabled?'启用':'禁用' }}</span></td>
                <td>
                  <div class="toolbar">
                    <button class="btn btn-ghost btn-xs" @click="toggleMod(m.raw)">{{ m.enabled?'禁用':'启用' }}</button>
                    <button class="btn btn-red btn-xs" @click="deleteMod(m.raw,m.name)">删除</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── 地图管理 ── -->
    <div v-if="page==='worlds'" class="page">
      <div class="page-header"><div class="page-title">地图管理</div></div>
      <div class="card">
        <div class="card-header">
          <span class="card-title">存档备份下载</span>
          <button class="btn btn-blue btn-sm" @click="backupWorld">⬇ 一键备份并下载</button>
        </div>
        <p style="color:var(--subtext);font-size:12px;">将服务器 Saves 目录打包下载到本地，可用于回档或迁移。</p>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">切换地图</span></div>
        <div class="toolbar" style="margin-bottom:16px;">
          <select class="form-select" v-model="selectedWorld" style="max-width:280px;">
            <option v-for="w in worlds" :key="w" :value="w">{{ w }}</option>
          </select>
          <button class="btn btn-primary btn-sm" @click="switchWorld">应用</button>
          <span style="color:var(--subtext);font-size:12px;">当前：{{ currentWorld||'未设置' }}</span>
        </div>
        <div class="toolbar" style="margin-bottom:14px;">
          <label class="btn btn-ghost btn-sm" style="cursor:pointer;">+ 上传地图（ZIP）<input type="file" accept=".zip" style="display:none" @change="uploadWorld"></label>
          <button class="btn btn-ghost btn-sm" @click="fetchWorlds">刷新</button>
        </div>
        <div class="world-list">
          <div v-for="w in worlds" :key="w" class="world-item" :class="{active:w===currentWorld}">
            <span class="world-name">{{ w }}</span>
            <span v-if="w===currentWorld" class="active-tag">✓ 当前</span>
            <button class="btn btn-red btn-xs" @click="deleteWorld(w)">删除</button>
          </div>
          <div v-if="worlds.length===0" class="empty-tip">暂无地图</div>
        </div>
      </div>
    </div>

    <!-- ── 服务器设置 ── -->
    <div v-if="page==='settings'" class="page">
      <div class="page-header"><div class="page-title">服务器设置</div></div>
      <div class="card" style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
        <span style="color:var(--subtext);font-size:13px;flex:1;">一键汉化：为 serverconfig.xml 配置项添加中文注释，操作前自动备份。</span>
        <button class="btn btn-orange btn-sm" :disabled="hanizeLoading" @click="hanizeConfig">{{ hanizeLoading?'汉化中…':'📝 一键汉化' }}</button>
      </div>
      <div class="card">
        <div class="form-grid">
          <template v-for="f in FIELD_DEFS" :key="f.key">
            <div class="form-group">
              <label class="form-label">{{ f.label }}</label>
              <input v-if="f.type==='text'||f.type==='number'" :type="f.type" class="form-input" v-model="serverConfig[f.key]" :min="f.min" :max="f.max" />
              <select v-else-if="f.type==='select'" class="form-select" v-model="serverConfig[f.key]">
                <option v-for="(o,i) in f.options" :key="o" :value="o">{{ f.labels[i] }}</option>
              </select>
              <select v-else-if="f.type==='region'" class="form-select" v-model="serverConfig[f.key]">
                <option v-for="r in REGION_OPTIONS" :key="r.value" :value="r.value">{{ r.label }}</option>
              </select>
              <div v-else-if="f.type==='bool'" style="display:flex;align-items:center;gap:8px;padding-top:4px;">
                <input type="checkbox" :checked="serverConfig[f.key]==='true'" @change="serverConfig[f.key]=$event.target.checked?'true':'false'" />
                <span style="color:var(--subtext);font-size:12px;">{{ serverConfig[f.key]==='true'?'已开启':'已关闭' }}</span>
              </div>
            </div>
          </template>
        </div>
        <div class="toolbar" style="margin-top:18px;">
          <button class="btn btn-primary" @click="saveServerConfig">保存配置</button>
          <button class="btn btn-ghost btn-sm" @click="fetchServerConfig">重新加载</button>
        </div>
      </div>
    </div>

    <!-- ── 辅助工具 ── -->
    <div v-if="page==='tools'" class="page">
      <div class="page-header"><div class="page-title">辅助工具</div></div>
      <div class="card">
        <div class="card-header"><span class="card-title">网络诊断</span></div>
        <div class="toolbar" style="margin-bottom:12px;">
          <button class="btn btn-blue btn-sm" @click="checkPorts">检查端口</button>
          <button class="btn btn-ghost btn-sm" @click="openFirewall">一键开放防火墙</button>
        </div>
        <div v-if="Object.keys(portResults).length">
          <div v-for="(used,port) in portResults" :key="port" class="port-row">
            <span class="port-num">{{ port }}</span>
            <span :class="used?'port-bad':'port-ok'">{{ used?'⚠ 被占用':'✓ 可用' }}</span>
          </div>
        </div>
        <div v-if="Object.keys(fwResults).length" style="margin-top:10px;">
          <div v-for="(ok,port) in fwResults" :key="port" class="port-row">
            <span class="port-num">{{ port }}</span>
            <span :class="ok?'port-ok':'port-bad'">{{ ok?'✓ 已开放':'✗ 失败' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 系统设置 ── -->
    <div v-if="page==='sysconfig'" class="page">
      <div class="page-header"><div class="page-title">系统设置</div></div>

      <div class="card">
        <div class="card-header"><span class="card-title">一键部署服务端</span></div>
        <p style="color:var(--subtext);font-size:12px;margin-bottom:12px;">使用 SteamCMD 自动下载安装七日杀服务端，下载过程在控制台实时显示。</p>
        <button class="btn btn-primary btn-sm" @click="installServer">🚀 一键下载 / 更新服务端</button>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">路径配置</span></div>
        <div class="form-grid single" style="gap:14px;">
          <div class="form-group">
            <label class="form-label">服务端目录</label>
            <div class="input-group">
              <input type="text" class="form-input" v-model="sysPaths.server_dir" placeholder="例：D:\\7DaysToDieServer" />
              <button class="btn btn-blue btn-sm" :disabled="autoSearching" @click="autoSearch" style="white-space:nowrap;">{{ autoSearching?'搜索中…':'🔍 自动搜索' }}</button>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">serverconfig.xml 路径</label>
            <input type="text" class="form-input" v-model="sysPaths.config_path" placeholder="例：D:\\7DaysToDieServer\\serverconfig.xml" />
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">Web 服务端口</span></div>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">监听地址</label>
            <input type="text" class="form-input" v-model="sysPaths.web_host" placeholder="0.0.0.0" />
          </div>
          <div class="form-group">
            <label class="form-label">监听端口</label>
            <input type="number" class="form-input" v-model="sysPaths.web_port" min="1024" max="65535" />
          </div>
        </div>
        <p style="color:var(--subtext);font-size:12px;margin-top:10px;">⚠ 修改端口后需重启 Web 服务生效。</p>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">账号管理</span></div>
        <p style="color:var(--subtext);font-size:13px;line-height:1.7;">
          当前登录账号：<strong style="color:var(--text);">{{ currentUser }}</strong><br>
          忘记密码：删除以下 <code style="color:var(--yellow);">users.json</code> 文件后刷新页面即可重新注册（用户配置同步清除）：<br>
          <code style="color:var(--accent);font-size:12px;word-break:break-all;">{{ usersFile || '（点击「刷新路径」加载）' }}</code>
        </p>
        <div class="toolbar" style="margin-top:12px;">
          <button class="btn btn-ghost btn-sm" @click="fetchUsersFile">刷新路径</button>
          <button class="btn btn-red btn-sm" @click="logout">退出登录</button>
        </div>
      </div>

      <div class="toolbar">
        <button class="btn btn-primary" @click="saveSysPaths">保存设置</button>
        <button class="btn btn-ghost btn-sm" @click="fetchSysPaths">重新加载</button>
      </div>
    </div>

  </div><!-- #main -->

  <!-- 移动端底部导航 -->
  <div class="bottom-nav">
    <button v-for="tab in bottomTabs" :key="tab.id" class="bottom-nav-btn" :class="{active:page===tab.id}" @click="switchPage(tab.id)">
      <span class="bnav-icon">{{ tab.icon }}</span>
      <span>{{ tab.label }}</span>
    </button>
  </div>

</div><!-- .app-shell -->

<!-- ══ 右键菜单 ════════════════════════════════════════════ -->
<div v-if="ctxMenu.show" class="ctx-menu" :style="{left:ctxMenu.x+'px',top:ctxMenu.y+'px'}" @click.stop>
  <div class="ctx-menu-header">{{ ctxMenu.player?.name }}</div>
  <div class="ctx-item" @click="execPlayerAction('kick')">🚫 踢出</div>
  <div class="ctx-item ctx-danger" @click="execPlayerAction('ban')">🔨 封禁</div>
  <div class="ctx-divider"></div>
  <div class="ctx-item" @click="execPlayerAction('admin')">⭐ 设为管理员</div>
  <div class="ctx-item" @click="execPlayerAction('unadmin')">✖ 撤销管理员</div>
  <div class="ctx-divider"></div>
  <div class="ctx-item" @click="execPlayerAction('unban')">✅ 解除封禁</div>
</div>

<!-- ══ 崩溃检测弹窗 ════════════════════════════════════════ -->
<div v-if="crashModal.show" class="modal-backdrop" @click.self="crashModal.show=false">
  <div class="modal">
    <div class="modal-header">
      <span class="modal-icon">🔍</span>
      <span class="modal-title">AI 崩溃检测报告</span>
      <button class="modal-close" @click="crashModal.show=false">✕</button>
    </div>
    <div class="modal-body">
      <div v-if="crashModal.loading" style="text-align:center;padding:32px;color:var(--subtext);">正在扫描最近日志…</div>
      <div v-else-if="!crashModal.found" style="text-align:center;padding:32px;">
        <div style="font-size:32px;margin-bottom:12px;">✅</div>
        <div style="color:var(--green);font-weight:600;">未检测到已知崩溃模式</div>
        <div style="color:var(--subtext);font-size:13px;margin-top:6px;">服务器日志目前看起来正常。</div>
      </div>
      <div v-else>
        <div v-for="issue in crashModal.issues" :key="issue.id" class="crash-issue">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            <span class="crash-lv" :class="issue.level">{{ issue.level.toUpperCase() }}</span>
          </div>
          <div class="crash-cause">{{ issue.cause }}</div>
          <div class="crash-kw">检测到关键词：{{ issue.keyword }}</div>
          <div class="crash-sol">{{ issue.solution }}</div>
        </div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-ghost btn-sm" @click="crashModal.show=false">关闭</button>
    </div>
  </div>
</div>

<!-- ══ 通用确认弹窗 ══════════════════════════════════════════ -->
<div v-if="modal.show" class="modal-backdrop" @click.self="closeModal">
  <div class="modal">
    <div class="modal-header">
      <span class="modal-icon">{{ modal.icon }}</span>
      <span class="modal-title">{{ modal.title }}</span>
      <button class="modal-close" @click="closeModal">✕</button>
    </div>
    <div class="modal-body">
      <p style="color:var(--subtext);line-height:1.8;white-space:pre-wrap;">{{ modal.content }}</p>
    </div>
    <div class="modal-footer">
      <button v-if="modal.type==='confirm'" class="btn btn-ghost btn-sm" @click="closeModal">{{ modal.cancelText }}</button>
      <button class="btn btn-sm" :class="modal.confirmClass" @click="confirmModal">{{ modal.confirmText }}</button>
    </div>
  </div>
</div>

<!-- ══ Toast ══════════════════════════════════════════════ -->
<div class="toast-container">
  <div v-for="t in toasts" :key="t.id" class="toast" :class="'toast-'+t.type">{{ t.msg }}</div>
</div>
  `,
}).mount('#app');
