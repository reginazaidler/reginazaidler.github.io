(function(){'use strict';
var KEY='vainzof_cookie_consent_v1';
function get(){try{return JSON.parse(localStorage.getItem(KEY)||'null');}catch(e){return null;}}
function save(analytics){var v={necessary:true,analytics:!!analytics,updated:new Date().toISOString()};localStorage.setItem(KEY,JSON.stringify(v));window.dispatchEvent(new CustomEvent('vainzof:consent',{detail:v}));return v;}
function banner(){
 if(get()) return;
 var ru=document.documentElement.lang==='ru';
 var el=document.createElement('div');el.id='cookie-consent';el.setAttribute('role','dialog');el.setAttribute('aria-label',ru?'Настройки cookie':'הגדרות עוגיות');
 el.style.cssText='position:fixed;z-index:99999;left:16px;right:16px;bottom:16px;max-width:760px;margin:auto;background:#fff;color:#0f172a;border:1px solid #cbd5e1;border-radius:14px;padding:18px;box-shadow:0 12px 40px rgba(15,23,42,.25);font:inherit';
 el.innerHTML=ru?'<strong>Cookie и статистика</strong><p style="margin:8px 0 14px">Необходимые cookie используются для работы сайта. Google Analytics загружается только после вашего согласия.</p><div style="display:flex;gap:8px;flex-wrap:wrap"><button data-accept>Разрешить статистику</button><button data-reject>Только необходимые</button><a href="/ru/politika-konfidentsialnosti.html">Подробнее</a></div>':'<strong>עוגיות ונתוני שימוש</strong><p style="margin:8px 0 14px">עוגיות הכרחיות משמשות להפעלת האתר. Google Analytics ייטען רק לאחר הסכמה.</p><div style="display:flex;gap:8px;flex-wrap:wrap"><button data-accept>אישור מדידה</button><button data-reject>הכרחיות בלבד</button><a href="/cookies.html">מידע נוסף</a></div>';
 el.querySelectorAll('button').forEach(function(b){b.style.cssText='padding:9px 14px;border:1px solid #1e3a5f;border-radius:8px;background:#fff;color:#1e3a5f;font-weight:700;cursor:pointer'});
 document.body.appendChild(el);
 el.querySelector('[data-accept]').onclick=function(){save(true);el.remove();};
 el.querySelector('[data-reject]').onclick=function(){save(false);el.remove();};
}
window.vainzofConsent={get:get,setAnalytics:save,reset:function(){localStorage.removeItem(KEY);location.reload();}};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',banner);else banner();
})();