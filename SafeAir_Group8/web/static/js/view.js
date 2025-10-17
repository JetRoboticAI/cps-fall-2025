// static/js/view.js
const $ = id => document.getElementById(id);
const card = document.getElementById('card');

function badge(el, kind, text){
  el.textContent = text;
  el.className = 'badge ' + kind; // ok | warn | neutral
}
function toNum(v){ return (v===0 || typeof v==='number') ? v : null; }

// 本地时间 + 相对时间
function formatTimestamp(ts){
  if(!ts) return 'Updated —';
  const d = new Date(ts);
  const now = new Date();
  const diffSec = Math.floor((now - d)/1000);

  const relative =
    diffSec < 10 ? 'just now' :
    diffSec < 60 ? `${diffSec}s ago` :
    diffSec < 3600 ? `${Math.floor(diffSec/60)}m ago` :
    `${Math.floor(diffSec/3600)}h ago`;

  const local = new Intl.DateTimeFormat(undefined, {
    hour: '2-digit', minute:'2-digit',
    day:'numeric', month:'short'
  }).format(d);

  return `Updated ${local} (${relative})`;
}

async function refresh(){
  try{
    const r = await fetch('/api/data', {cache: 'no-store'});
    const d = await r.json();

    // 更新时间（美化）
    $('lastUpdated').textContent = formatTimestamp(d.ts);

    // PIR
    const motion = toNum(d?.sensors?.pir?.motion);
    if (motion === 1) badge($('pirMsg'), 'warn', 'Human motion detected');
    else if (motion === 0) badge($('pirMsg'), 'ok', 'No human motion detected');
    else badge($('pirMsg'), 'neutral', '—');

    // DHT11
    const t = d?.sensors?.dht11?.temperature_c;
    const h = d?.sensors?.dht11?.humidity_pct;
    $('tempC').textContent = (typeof t === 'number') ? t : '—';
    $('humPct').textContent = (typeof h === 'number') ? h : '—';

    // MQ-2
    const mq2 = toNum(d?.sensors?.mq2?.state);
    let alertOn = false;
    if (mq2 === 0){ badge($('mq2Msg'), 'warn', 'Harmful gas detected!'); alertOn = true; }
    else if (mq2 === 1){ badge($('mq2Msg'), 'ok', 'No harmful gas detected'); }
    else { badge($('mq2Msg'), 'neutral', '—'); }

    // Buzzer
    const bz = d?.alarm?.buzzer_on;
    if (bz === true) badge($('buzzerMsg'), 'warn', 'ON');
    else if (bz === false) badge($('buzzerMsg'), 'ok', 'OFF');
    else badge($('buzzerMsg'), 'neutral', '—');

    // 警报风格
    card.classList.toggle('alert', !!alertOn);
  } catch (e){
    $('lastUpdated').textContent = 'Updated — (error)';
    console.error(e);
  }
}

refresh();
setInterval(refresh, 3000);
