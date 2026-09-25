/* SituSnap reconstructive UI surgery — Option 1
   Visual layer only. Does not change Breadcrumbs, camera, vault or persistence. */
(() => {
  const CSS = `
  :root{--ss-navy:#061827;--ss-green:#27df67;--ss-deep:#008b68;--ss-ink:#0b1b30}
  html,body{overflow-x:hidden!important}
  body{background:#f4f6f8!important;color:var(--ss-ink)!important}
  header{
    height:82px!important;background:var(--ss-navy)!important;padding:0 15px!important;
    box-shadow:none!important;position:sticky!important;top:0!important
  }
  .brand{gap:10px!important}.brand-mark,.brand-mark svg{width:54px!important;height:54px!important}
  .brand-name{font-size:25px!important;line-height:1!important}
  .tag{font-size:11px!important;letter-spacing:0!important;color:#fff!important;margin-top:5px!important}
  header .menu{background:transparent!important;border:0!important;color:#fff!important;font-size:30px!important}
  main{padding:0 0 92px!important;max-width:680px!important}
  .ss-home-shell{
    background:#fff!important;border:0!important;border-radius:0!important;
    box-shadow:0 2px 10px #00000012!important;margin:0!important;padding:18px 14px 14px!important;
    overflow:hidden!important
  }
  .ss-home-shell:before,.ss-home-kicker,.ss-home-copy{display:none!important}
  #ssHomeTitle{
    display:block!important;color:#071a33!important;white-space:nowrap!important;
    font-size:clamp(19px,5.15vw,29px)!important;line-height:1.1!important;
    letter-spacing:-.9px!important;margin:0 0 16px!important;width:100%!important
  }
  .ss-find-card{background:#fff!important;padding:0!important;box-shadow:none!important}
  .ss-find-card input{
    box-sizing:border-box!important;height:58px!important;min-height:58px!important;
    border:1px solid #d4dce5!important;border-radius:12px!important;background:#fff!important;
    color:#334155!important;-webkit-text-fill-color:#334155!important;
    font-size:15px!important;font-weight:650!important;padding:12px 14px!important
  }
  #huntPostcode{font-size:15px!important}
  .ss-address-row{
    display:grid!important;grid-template-columns:108px minmax(0,1fr)!important;
    gap:10px!important;margin-top:11px!important;align-items:stretch!important
  }
  .ss-address-row .ss-field{margin:0!important;min-width:0!important}
  #doorNumber{
    width:100%!important;font-size:12px!important;padding:10px 8px!important;
    letter-spacing:-.35px!important
  }
  #manualAddress{width:100%!important;font-size:13px!important;padding:10px!important;letter-spacing:-.25px!important}
  .ss-find-primary{
    width:100%!important;height:62px!important;min-height:62px!important;margin-top:13px!important;
    border-radius:12px!important;background:linear-gradient(135deg,#00a06d,#007c68)!important;
    color:#fff!important;font-size:18px!important;font-weight:950!important;letter-spacing:0!important;
    box-shadow:0 10px 22px rgba(0,128,93,.18)!important
  }
  .ss-secondary{
    width:100%!important;min-height:54px!important;margin:10px 0 0!important;border-radius:12px!important;
    background:#fff!important;color:#116a3d!important;border:1px solid #b6dec3!important;font-size:15px!important
  }
  #reminderCard{
    margin:12px!important;background:linear-gradient(155deg,#122b49,#071a2d)!important;
    color:#fff!important;border:0!important;border-radius:20px!important;
    box-shadow:0 10px 25px rgba(5,24,39,.18)!important;padding:18px!important
  }
  #reminderCard h2{color:#fff!important;font-size:23px!important;line-height:1.1!important;margin:0 0 8px!important}
  #reminderCard p,#reminderCard .muted,#reminderCard .small-note{color:#d8e1ec!important}
  #reminderCard .details{
    background:#0c2744!important;border:1px solid #294662!important;border-radius:14px!important;
    color:#fff!important;margin-top:12px!important
  }
  #reminderCard .details summary{color:#fff!important;font-weight:850!important}
  #reminderCard label{color:#dce6f2!important}
  .bottom{
    background:#061827!important;height:72px!important;padding:5px 4px 7px!important;border:0!important
  }
  .nav{color:#aeb8c5!important;font-size:10px!important}
  .nav.active{color:#34e66b!important;background:transparent!important;border-bottom:3px solid #34e66b!important;border-radius:0!important}
  .nav .ico{font-size:21px!important}
  @media(max-width:380px){
    #ssHomeTitle{font-size:18px!important;letter-spacing:-.8px!important}
    .ss-address-row{grid-template-columns:104px minmax(0,1fr)!important}
    #doorNumber{font-size:11.5px!important}
    #manualAddress{font-size:12.5px!important}
  }`;

  function install(){
    if (!document.getElementById('ssOption1Surgery')) {
      const st=document.createElement('style');
      st.id='ssOption1Surgery';
      st.textContent=CSS;
      document.head.appendChild(st); // deliberately LAST: beats legacy inline styles
    }

    const mark=document.querySelector('.brand-mark');
    if(mark) mark.innerHTML=`<svg viewBox="0 0 100 100" role="img" aria-label="SituSnap">
      <rect x="3" y="3" width="94" height="94" rx="25" fill="#061827"/>
      <path d="M50 10c-19 0-34 15-34 34 0 25 34 47 34 47s34-22 34-47c0-19-15-34-34-34z" fill="#39e36f"/>
      <circle cx="50" cy="41" r="17" fill="#061827"/>
      <path d="M35 60c12-2 22-8 33-18M39 68c11-2 20-7 29-14" fill="none" stroke="#061827" stroke-width="7" stroke-linecap="round"/>
    </svg>`;

    const tag=document.querySelector('.tag');
    if(tag) tag.textContent='Find it. Snap it. Update it.';

    const find=document.querySelector('.ss-find-primary');
    if(find) find.textContent='⌕  START HUNT';

    const title=document.getElementById('ssHomeTitle');
    if(title) title.textContent='Find it. Snap it. Update it.';

    const num=document.getElementById('doorNumber');
    if(num) num.placeholder='NUMBER';

    const hand=document.querySelector('#reminderCard h2');
    if(hand) hand.textContent='Found / Not Found Handover';
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',install,{once:true});
  else install();
})();
