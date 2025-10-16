// web/static/js/main.js

// ====== dom helpers ======
const $ = (id) => document.getElementById(id);
const muteBtn     = $('muteBtn');

// 弹窗元素
const backdrop    = $('alertBackdrop');
const amMsg       = $('amMsg');
const btnConfirm  = $('amConfirm');
const btnLater    = $('amCancel');

function showAlertModal(message) {
  if (!backdrop) return;
  if (message && amMsg) amMsg.textContent = message;
  backdrop.classList.add('show');
  backdrop?.setAttribute('aria-hidden', 'false');
}
function hideAlertModal() {
  if (!backdrop) return;
  backdrop.classList.remove('show');
  backdrop?.setAttribute('aria-hidden', 'true');
}
if (btnConfirm) btnConfirm.onclick = hideAlertModal;
if (btnLater)   btnLater.onclick   = hideAlertModal;


// ====== 点击 “Mute Buzzer” -> 设置本次告警静音（snooze=true） ======
if (muteBtn) {
  muteBtn.addEventListener('click', async (e) => {
    // 被置灰时不处理
    if (muteBtn.classList.contains('disabled')) return;
    e.preventDefault();
    try {
      await fetch('/api/mute', { method: 'POST' });
      // 立刻置灰，等下次轮询再同步状态
      muteBtn.classList.add('disabled');
      muteBtn.setAttribute('aria-disabled', 'true');
    } catch (err) {
      console.error('mute failed', err);
    }
  });
}


// ====== 弹窗控制（只出现一次/本次事件） ======
const ACK_KEY = 'sa_alert_ack_active';  // localStorage 键

function acknowledgeOnce() {
  localStorage.setItem(ACK_KEY, '1');
  hideAlertModal();
}
if (btnConfirm) btnConfirm.addEventListener('click', acknowledgeOnce);
if (btnLater)   btnLater.addEventListener('click',  acknowledgeOnce);


// ====== 轮询数据：决定按钮状态、弹窗出现 ======
let prevMq2 = 1;          // 上次 MQ-2 状态
let lastAlertAt = 0;
const ALERT_INTERVAL_MS = 30000;

async function refreshMain() {
  try {
    const res = await fetch('/api/data', { cache: 'no-store' });
    const d = await res.json();

    const isOn   = d?.alarm?.buzzer_on === true;
    const snooze = d?.alarm?.snoozed   === true;
    const mq2    = Number(d?.sensors?.mq2?.state);

    // --- 控制按钮 ---
    if (muteBtn) {
      if (isOn && !snooze) {
        muteBtn.classList.remove('disabled');
        muteBtn.setAttribute('aria-disabled', 'false');
      } else {
        muteBtn.classList.add('disabled');
        muteBtn.setAttribute('aria-disabled', 'true');
      }
    }

    // --- 弹窗逻辑 ---
    const now = Date.now();
    const alertActive = (mq2 === 0);   // 0 = 有气体

    if (alertActive && !snooze) {
      const alreadyAcked = localStorage.getItem(ACK_KEY) === '1';
      if (!alreadyAcked) {
        if (prevMq2 !== 0 || (now - lastAlertAt) > ALERT_INTERVAL_MS) {
          showAlertModal('Harmful gas detected! Please ventilate and check the source.');
          lastAlertAt = now;
        }
      }
    } else {
      // 回到安全态：清除已确认标记并隐藏弹窗
      localStorage.removeItem(ACK_KEY);
      hideAlertModal();
    }

    if (mq2 === 0 || mq2 === 1) prevMq2 = mq2;

  } catch (e) {
    // 网络错误时禁用按钮
    if (muteBtn) {
      muteBtn.classList.add('disabled');
      muteBtn.setAttribute('aria-disabled', 'true');
    }
    console.error(e);
  }
}

refreshMain();
setInterval(refreshMain, 3000);
