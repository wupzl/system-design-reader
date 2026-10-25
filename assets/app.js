(() => {
  const root = document.documentElement;
  const read = key => { try { return localStorage.getItem(key); } catch { return null; } };
  const save = (key, value) => { try { localStorage.setItem(key, value); } catch {} };
  const themes = ['white', 'light', 'dark'];
  const labels = { white: '纯白', light: '米白', dark: '深色' };
  let theme = themes.includes(read('reader-theme')) ? read('reader-theme') : 'white';
  const themeButton = document.getElementById('theme');
  const applyTheme = () => {
    root.dataset.theme = theme;
    themeButton.textContent = labels[theme];
    themeButton.setAttribute('aria-label', `切换背景，当前${labels[theme]}`);
    themeButton.title = '切换：纯白 → 米白 → 深色';
  };
  themeButton.addEventListener('click', () => {
    theme = themes[(themes.indexOf(theme) + 1) % themes.length];
    applyTheme();
    save('reader-theme', theme);
  });
  let size = Number(read('reader-size')) || 18;
  const resize = delta => {
    size = Math.min(26, Math.max(16, size + delta));
    root.style.setProperty('--reading-size', `${size}px`);
    document.getElementById('smaller').disabled = size === 16;
    document.getElementById('larger').disabled = size === 26;
    save('reader-size', size);
  };
  document.getElementById('smaller').addEventListener('click', () => resize(-1));
  document.getElementById('larger').addEventListener('click', () => resize(1));
  applyTheme();
  resize(0);
})();
