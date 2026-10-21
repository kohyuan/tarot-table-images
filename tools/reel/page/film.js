// タロットテーブル リール（本物の動画）の画面。中身は params.js の window.PARAMS から読む。
// 流れ：表のカードが一列に流れ込み、裏返って3枚に集まる → 問いを出して3.5秒考えてもらう
// → 左・中・右を1枚ずつめくる（1枚7秒）→ 3枚を並べて見せる → アプリと同じホーム画面で締める
// 時間割は固定（33.3秒）。音は ../audio/<正逆3文字>.m4a を、書き出しの道具が重ねる。
(function () {
  const P = window.PARAMS;

  // —— カードの名前（card_id の決まりは作業書のとおり）——
  const MAJ = ['愚者', '魔術師', '女教皇', '女帝', '皇帝', '教皇', '恋人', '戦車', '力', '隠者', '運命の輪', '正義', '吊るされた男', '死神', '節制', '悪魔', '塔', '星', '月', '太陽', '審判', '世界'];
  const ROMAN = ['0', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX', 'XXI'];
  const SUIT = { W: 'ワンド', C: 'カップ', S: 'ソード', P: 'ペンタクル' };
  const RANK = { 1: 'エース', 11: 'ペイジ', 12: 'ナイト', 13: 'クイーン', 14: 'キング' };
  function cardInfo(id) {
    const n = parseInt(id.slice(1), 10);
    if (id[0] === 'M') return { name: MAJ[n], num: ROMAN[n], suit: '' };
    return { name: `${SUIT[id[0]]}の${RANK[n] || n}`, num: '', suit: SUIT[id[0]] };
  }
  const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const br = s => esc(s).replace(/\n/g, '<br>');

  // 見出し「明日からの7日間 10/23(金)~10/29(木)のお金・買い物」を、上の小さい行とテーマに分ける
  const theme = P.theme || (P.headline.match(/\)の(.+)$/) || [, ''])[1];
  const subLine = theme && P.headline.endsWith(theme) ? P.headline.slice(0, -theme.length) : P.headline;
  const T = {
    sub: subLine, main: theme, q: P.question,
    stop: '直感で、左・中・右から<br>一枚選んでください',
    end1: 'あなただけの悩みを読みます。', end2: '詳しくはタロットテーブルへ。', en: 'The AI Tarot Table', ja: 'タロットテーブル', btn: '占いを始める',
  };
  // めくる3枚（左・中・右）。逆位置はカードごと上下逆さにする
  const PICKS = P.cards.map(c => ({ ...cardInfo(c.id), id: c.id, rev: c.pos === 'R', word: c.keyword || '', read: c.reading || '', art: c.art || null }));
  // 一列で流すカード：絵のあるカード。少なければ絵の無いカードの仮の表面を混ぜる
  const RIB_SRC = (P.ribbon && P.ribbon.length ? P.ribbon : []).slice();
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const pr = (t, a, b) => clamp((t - a) / (b - a));
  const lerp = (a, b, p) => a + (b - a) * p;
  const eo = p => 1 - Math.pow(1 - p, 3);
  const eio = p => (p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
  const body = document.body;
  const el = (cls, html = '') => { const e = document.createElement('div'); e.className = 'abs ' + cls; e.innerHTML = html; body.appendChild(e); return e; };
  const show = (e, op, x, y, s = 1, extra = '') => { e.style.opacity = op.toFixed(3); e.style.transform = `translate(${x}px,${y}px) scale(${s}) ${extra}`; };

  // —— 時間 ——
  const SETTLE = 2.55, H0 = 2.5, Q0 = 2.9, THINK0 = 3.2, THINK1 = 6.7;      // 問いを出し、3.5秒考えてもらう
  const SEG0 = 6.9, PER = 7.0;                                            // 1枚7秒
  const SUM0 = SEG0 + PER * 3, HOME0 = SUM0 + 1.8, DUR = HOME0 + 3.6;      // 3枚を並べて見せる → ホーム画面
  const seg = i => SEG0 + PER * i;

  // 空の星（アプリと同じ考え方）
  let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const sky = document.getElementById('sky'); let svg = '<svg width="1080" height="1920" style="position:absolute;inset:0">'; const tw = [];
  for (let i = 0; i < 160; i++) { const y = Math.pow(rnd(), 1.6) * 100; const r = rnd() < .9 ? .5 + rnd() * .7 : 1.2 + rnd() * .8; const o = (.2 + rnd() * .8) * .75 * (1 - y / 140);
    svg += `<circle id="s${i}" cx="${(rnd() * 1080).toFixed(1)}" cy="${(y * 19.2).toFixed(1)}" r="${(r * 2.4).toFixed(2)}" fill="#f1e6cf" opacity="${o.toFixed(2)}"/>`; if (r > 1.2) tw.push({ i, o, ph: rnd() * 6.28 }); }
  sky.innerHTML = svg + '</svg>';
  const twEls = tw.map(s => ({ ...s, e: document.getElementById('s' + s.i) }));

  const STAR = '<svg class="pstar" viewBox="-10 -10 20 20"><path d="M0 -10 Q1.6 -1.6 10 0 Q1.6 1.6 0 10 Q-1.6 1.6 -10 0 Q-1.6 -1.6 0 -10Z" fill="#e8c983"/></svg>';
  const CW = 560, CH = 933, SMALL = .5, XS = [230, 540, 850], ROWY = 930, BIGY = 885;
  // 表面：絵があれば絵＋決めてある仕上げ（内側の金線、下の暗い帯に金の番号と名前）、無ければ仮の表面
  function faceHTML(info, art) {
    const label = `<div class="label">${info.num ? `<span class="num">${info.num}</span>` : ''}${esc(info.name)}</div>`;
    if (art) return { cls: 'side face', html: `<img src="${art}"><div class="band"></div><div class="line"></div>${label}<div class="sheen"></div>` };
    return { cls: 'side face plain', html: `<div class="frame"></div><div class="frame2"></div>${info.num ? `<div class="pnum">${info.num}</div>` : ''}${STAR}<div class="pname" style="font-size:${Math.min(68, Math.floor(460 / (info.name.length * 1.12)))}px">${esc(info.name)}</div>${info.suit ? `<div class="psuit">${info.suit}</div>` : ''}<div class="sheen"></div>` };
  }
  function makeCard(info, art) {
    const c = el('card');
    const b = document.createElement('div'); b.className = 'side back'; b.innerHTML = '<img src="card_back.png">'; c.appendChild(b);
    let f = null;
    if (info) { const fh = faceHTML(info, art); f = document.createElement('div'); f.className = fh.cls; f.innerHTML = fh.html; c.appendChild(f); }
    return { c, b, f };
  }
  const sub = el('sub', esc(T.sub)), main = el('main', `<span>${esc(T.main)}</span>`);
  const halo = el('halo');

  // —— 始まり：一列のカード ——
  const N = 25, SP = 150, J0 = 17;
  const head = t => { const p = pr(t, 0, 1.45); return lerp(170, 100 - J0 * SP, 1 - (1 - p) * (1 - p)); };
  const FILL = ['M17', 'M19', 'M01', 'C02', 'M10', 'W03', 'M21', 'P10', 'M06', 'S06', 'M02', 'C10'];   // 絵が少ないときに混ぜる仮の表面
  const ribList = Array.from({ length: N }, (_, j) => RIB_SRC.length >= 3 ? RIB_SRC[j % RIB_SRC.length] : (RIB_SRC.length && j % 3 === 0 ? RIB_SRC[(j / 3) % RIB_SRC.length] : { id: FILL[j % FILL.length], art: null }));
  const RIB = ribList.map((r, j) => ({ ...makeCard(cardInfo(r.id), r.art), j }));
  const keep = { 17: 0, 20: 1, 23: 2 }, into = { 18: 0, 19: 1, 21: 1, 22: 2 };
  const FLIP_T = j => 1.5 + (j - J0) * .06, GATHER = 2.05;
  const ribPose = (j, t) => { const x = head(t) + j * SP, k = (x - 540) / 540; return { x, y: ROWY + k * k * 80, rot: k * 7, s: .54 + .14 * Math.exp(-Math.pow((x - 540) / 260, 2)) }; };

  // —— 盤面の3枚 ——
  const cards = PICKS.map(p => ({ ...makeCard(p, p.art), p }));
  cards.forEach(k => { k.sheen = k.f.querySelector('.sheen'); });
  const pos = ['左', '中', '右'].map(s => el('pos', s));
  const kws = PICKS.map(p => el('kw', '<span>' + esc(p.word || p.name) + '</span>'));
  const q = el('q', esc(T.q)), stop = el('stop', T.stop), bar = el('bar', '<i></i>'), barI = bar.querySelector('i');
  const cnames = PICKS.map(p => el('cname', `${esc(p.name)}<small>${p.rev ? '逆位置' : '正位置'}</small>${p.word ? `<b>${esc(p.word)}</b>` : ''}`));
  const reads = PICKS.map(p => el('read', br(p.read)));
  seed = 5; const motes = Array.from({ length: 30 }, () => ({ e: el('mote'), a: rnd() * 6.283, r: 250 + rnd() * 260, sp: 30 + rnd() * 60, s: .5 + rnd() * .9, ph: rnd() * 6.28, d: rnd() * 1.2 }));
  const sparks = XS.map(() => Array.from({ length: 8 }, () => el('mote')));
  // 締め（アプリのホーム画面と同じ部品）
  const hCard = makeCard(null), nameEn = el('nameEn', T.en), name = el('name', T.ja), lead = el('lead', `${T.end1}<br>${T.end2}`), btn = el('btn', T.btn), ring = el('ring');

  // 文の大きさを、枠に収まるように合わせる（問いは3行まで、読みは3行まで、見出しのテーマは1行）
  function fit(e, maxH, sizes) { for (const fs of sizes) { e.style.fontSize = fs + 'px'; if (e.scrollHeight <= maxH) return; } }

  // カードの姿勢を作る（めくっている途中・逆位置を含む）
  function cardTransform(k, face, kx, rot) { if (k.f) k.f.style.opacity = face ? 1 : 0; k.b.style.opacity = face ? 0 : 1;
    const r = rot + (face && k.p && k.p.rev ? 180 : 0); return `rotate(${r.toFixed(2)}deg) scaleX(${kx.toFixed(3)})`; }

  function render(t) {
    twEls.forEach(s => s.e.setAttribute('opacity', (s.o * (.55 + .45 * Math.sin(t * 1.3 + s.ph))).toFixed(3)));
    const homeOut = eio(pr(t, HOME0, HOME0 + .6));

    RIB.forEach(r => {
      if (t >= SETTLE) { r.c.style.opacity = 0; return; }
      let { x, y, rot, s } = ribPose(r.j, Math.min(t, 1.45)), op = 1;
      const fu = pr(t, FLIP_T(r.j), FLIP_T(r.j) + .18), kx = fu > 0 && fu < 1 ? Math.max(.02, Math.abs(Math.cos(Math.PI * fu))) : 1, face = fu < .5;
      r.f.style.opacity = face ? 1 : 0; r.b.style.opacity = face ? 0 : 1;
      const g = eio(pr(t, GATHER, SETTLE));
      if (r.j in keep || r.j in into) { const i = r.j in keep ? keep[r.j] : into[r.j]; x = lerp(x, XS[i], g); y = lerp(y, ROWY, g); rot = lerp(rot, 0, g); s = lerp(s, SMALL, g); if (r.j in into) op = 1 - pr(t, SETTLE - .2, SETTLE); }
      else { x = x + g * (x < 540 ? -300 : 300); op = 1 - g; }
      r.c.style.zIndex = (r.j in keep ? 40 : 20) + Math.round(30 - Math.abs(x - 540) / 40);
      show(r.c, op, x - CW / 2, y - CH / 2, s, `rotate(${rot.toFixed(2)}deg) scaleX(${kx.toFixed(3)})`);
    });

    const anyBig = Math.max(...PICKS.map((_, i) => eio(pr(t, seg(i), seg(i) + .6)) * (1 - eio(pr(t, seg(i) + PER - .6, seg(i) + PER)))));
    show(sub, pr(t, H0, H0 + .5) * (1 - homeOut), 0, 160 + (1 - eo(pr(t, H0, H0 + .6))) * 14);
    show(main, pr(t, H0 + .2, H0 + .8) * (1 - .45 * anyBig) * (1 - homeOut), 0, 205 + (1 - eo(pr(t, H0 + .2, H0 + .9))) * 18);

    const qIn = pr(t, Q0, Q0 + .5), qOut = pr(t, THINK1, THINK1 + .3);
    show(q, qIn * (1 - qOut), 0, 425 + (1 - eo(qIn)) * 16);
    show(stop, pr(t, THINK0, THINK0 + .3) * (1 - qOut), 0, 1320 + (1 - eo(pr(t, THINK0, THINK0 + .4))) * 20);
    show(bar, pr(t, THINK0, THINK0 + .3) * (1 - qOut), 0, 1530);
    barI.style.transform = `scaleX(${(1 - pr(t, THINK0, THINK1)).toFixed(4)})`;

    cards.forEach((k, i) => {
      if (t < SETTLE) { [k.c, cnames[i], reads[i], kws[i], ...sparks[i]].forEach(e => e.style.opacity = 0); return; }
      const s0 = seg(i), up = eio(pr(t, s0, s0 + .6)), down = eio(pr(t, s0 + PER - .6, s0 + PER));
      const flip = pr(t, s0 + .6, s0 + 1.1);
      const settle = Math.sin(Math.PI * pr(t, SETTLE, SETTLE + .25)) * 6;
      let others = 0; PICKS.forEach((_, m) => { if (m !== i) others = Math.max(others, eio(pr(t, seg(m), seg(m) + .5)) * (1 - eio(pr(t, seg(m) + PER - .5, seg(m) + PER)))); });
      const big = up * (1 - down);
      let x = lerp(XS[i], 540, big), y = lerp(ROWY - settle, BIGY, big), s = lerp(SMALL, 1, big) * (1 + .03 * eio(pr(t, s0 + 1.1, s0 + PER - .6)) * big);
      const sum = eio(pr(t, SUM0, SUM0 + .5)); s *= 1 + .16 * sum; y -= 40 * sum; x = lerp(x, [205, 540, 875][i], sum);
      let kx = 1; if (flip > 0 && flip < 1) kx = Math.max(.002, Math.abs(Math.cos(Math.PI * flip)));
      const face = t >= s0 + .85;
      k.c.style.zIndex = big > .01 ? 70 : 50;
      show(k.c, (1 - others) * (1 - homeOut), x - CW / 2, y - CH / 2, s, cardTransform(k, face, kx, 0));
      const su = pr(t, s0 + 1.15, s0 + 2.0); k.sheen.style.opacity = su > 0 && su < 1 ? 1 : 0; k.sheen.style.transform = `translateX(${lerp(-110, 110, eio(su))}%)`;
      const lu = pr(t, SETTLE - .02, SETTLE + .5);
      sparks[i].forEach((m, j) => { const a = -Math.PI / 2 + (j - 3.5) * .38, d = 140 + 120 * eo(lu); show(m, lu > 0 && lu < 1 ? 1 - lu : 0, XS[i] + Math.cos(a) * d * .9, ROWY + 210 + Math.sin(a) * d * .25 + 20, .8); });
      const cin = pr(t, s0 + 1.5, s0 + 1.9) * (1 - down), rin = pr(t, s0 + 2.0, s0 + 2.4) * (1 - down);
      show(cnames[i], cin, 0, 1385 + (1 - eo(pr(t, s0 + 1.5, s0 + 2.0))) * 16);
      show(reads[i], rin, 0, 1478 + (1 - eo(pr(t, s0 + 2.0, s0 + 2.5))) * 16);
      show(kws[i], pr(t, SUM0 + .3 + .12 * i, SUM0 + .7 + .12 * i) * (1 - homeOut), [205, 540, 875][i] - 160, ROWY + 290);
    });
    let hu = 0; PICKS.forEach((_, i) => { const u = pr(t, seg(i) + .85, seg(i) + 1.4) * (1 - pr(t, seg(i) + PER - .6, seg(i) + PER)); if (u > hu) hu = u; });
    show(halo, eo(hu) * .85, 540 - 450, BIGY - 450, .7 + .4 * eo(hu));
    motes.forEach(m => { const i = PICKS.findIndex((_, n) => t >= seg(n) + .9 && t < seg(n) + PER - .5); if (i < 0) { m.e.style.opacity = 0; return; }
      const u = t - seg(i) - .9 - m.d; if (u <= 0) { m.e.style.opacity = 0; return; }
      const y = BIGY + Math.sin(m.a) * m.r * .9 - u * m.sp, x = 540 + Math.cos(m.a) * m.r * .75 + Math.sin(u * 1.2 + m.ph) * 14;
      show(m.e, clamp(u / .5) * (.35 + .65 * Math.abs(Math.sin(u * 2 + m.ph))) * .85, x, y, m.s); });
    pos.forEach((p, i) => show(p, pr(t, 2.7 + .1 * i, 3.1 + .1 * i) * (1 - pr(t, SEG0, SEG0 + .3)), XS[i] - 80, ROWY + CH * SMALL / 2 + 26));

    const hc = pr(t, HOME0 + .3, HOME0 + .8);
    show(hCard.c, hc, 540 - CW / 2, 560 - CH / 2, 200 / CW * (1 + .04 * (1 - eo(hc))), cardTransform(hCard, false, 1, 0));
    show(nameEn, pr(t, HOME0 + .6, HOME0 + 1.0), 0, 846); show(name, pr(t, HOME0 + .75, HOME0 + 1.15), 0, 900 + (1 - eo(pr(t, HOME0 + .75, HOME0 + 1.2))) * 20);
    show(lead, pr(t, HOME0 + 1.2, HOME0 + 1.6), 0, 1170);
    const press = pr(t, DUR - 1.1, DUR - .85); btn.style.opacity = pr(t, HOME0 + 1.7, HOME0 + 2.0).toFixed(3); btn.style.transform = `translate(0px,1430px) scale(${1 - .04 * Math.sin(Math.PI * press)})`; btn.style.background = press > 0 && press < 1 ? '#d6dbea' : '#e9ecf5';
    const ru = pr(t, DUR - 1.12, DUR - .6); show(ring, ru > 0 && ru < 1 ? 1 - ru : 0, 600, 1420, .5 + 1.4 * eo(ru));
  }
  window.DUR = DUR; window.render = render;
  window.CHECK = () => ({ q: q.scrollHeight, reads: reads.map(r => r.scrollHeight), main: main.firstChild.offsetWidth });
  const ALL = Object.values(T).join('') + '左中右正位置逆位置' + PICKS.map(p => p.name + p.word + p.read).join('') + RIB.length + ribList.map(r => cardInfo(r.id).name).join('') + Object.values(SUIT).join('');
  Promise.all([
    document.fonts.load("700 60px 'Zen Old Mincho'", ALL), document.fonts.load("500 40px 'Zen Kaku Gothic New'", ALL), document.fonts.load('400 40px Marcellus', ROMAN.join('') + ' The AI Tarot Table'),
    document.fonts.load("400 40px 'Kaisei Decol'", T.ja), ...[...document.images].map(i => i.decode().catch(() => {})),
  ]).then(() => {
    fit(q, 270, [54, 50, 46, 42]); reads.forEach(r => fit(r, 230, [42, 39, 36, 33]));
    kws.forEach(k => { for (const fs of [34, 30, 27, 24]) { k.style.fontSize = fs + 'px'; if (k.firstChild.offsetWidth <= 310) break; } });
    main.style.whiteSpace = 'nowrap'; for (const fs of [112, 100, 88, 76, 66]) { main.style.fontSize = fs + 'px'; if (main.firstChild.offsetWidth <= 1000) break; }
    render(0); window.READY = true;
  });
})();
