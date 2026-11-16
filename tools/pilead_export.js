// Export Pi-Lead wrong-question notebook to a JSON file for MathMastery.
// Runs inside a logged-in Pi-Lead Notebook tab (https://pilead-edu.net/notebook/...).
// Read-only: it only GETs the notebook API and the question images.
// `python tools/make_bookmarklet.py` turns this file into a bookmark URL.
(async () => {
  if (!location.pathname.startsWith('/notebook')) {
    alert('Open your Pi-Lead Notebook first (Hub → Review Task), then click this bookmark again.');
    return;
  }
  const get = (u) => fetch(u, { credentials: 'include' }).then((r) => {
    if (!r.ok) throw new Error(r.status + ' ' + u);
    return r.json();
  });
  const toDataUrl = async (u) => {
    const r = await fetch(u, { credentials: 'include' });
    if (!r.ok) throw new Error('missing');
    const blob = await r.blob();
    if (!blob.type.startsWith('image/')) throw new Error('not a picture');
    return await new Promise((res) => { const f = new FileReader(); f.onload = () => res(f.result); f.readAsDataURL(blob); });
  };
  try {
    const notebooks = await get('/notebook/api/notebooks');
    const items = [];
    for (const nb of notebooks) {
      let page = 1, pages = 1;
      do {
        const l = await get(`/notebook/api/error-items/list?subjectId=${nb.id}&page=${page}&pageSize=100&sort=newest`);
        for (const x of l.items) {
          items.push({
            id: x.id, subject: nb.name, questionText: x.questionText || '', answerText: x.answerText || '',
            analysis: x.analysis || '', errorType: x.errorType || '', knowledgePoints: x.knowledgePoints || '[]',
            source: x.source || '', difficultyLevel: x.difficultyLevel, mistakeStatus: x.mistakeStatus,
            originalImageUrl: x.originalImageUrl || '', createdAt: x.createdAt,
          });
        }
        pages = l.totalPages || 1;
        page++;
      } while (page <= pages);
    }
    // Embed pictures referenced in question/explanation text so MathMastery can show them offline
    const images = {};
    for (const it of items) {
      for (const m of (it.questionText + '\n' + it.analysis).matchAll(/!\[[^\]]*\]\(([^)\s]+)\)/g)) {
        const u = m[1];
        if (!u.startsWith('data:') && !images[u]) {
          try { images[u] = await toDataUrl(u); } catch (e) { /* missing picture: skip */ }
        }
      }
    }
    const out = { exportedAt: new Date().toISOString(), source: 'pilead', items, images };
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(out)], { type: 'application/json' }));
    a.download = `pilead_export_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    alert(`Exported ${items.length} questions. Now drop the downloaded file into MathMastery → Add Questions → Import from Pi-Lead.`);
  } catch (e) {
    alert('Export failed: ' + e.message + '\nMake sure you are logged in to Pi-Lead and on the Notebook page.');
  }
})();
