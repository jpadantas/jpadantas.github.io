<script>
(function(){
  const modal = document.getElementById('bibtexModal');
  const pre = document.getElementById('bibtexPre');
  const closeBtn = modal.querySelector('.close');
  const copyBtn = document.getElementById('bibtexCopyBtn');
  const downloadLink = document.getElementById('bibtexDownloadLink');

  let currentBibUrl = null;

  async function openFromUrl(url){
    try{
      pre.textContent = 'Carregando…';
      currentBibUrl = url;
      const res = await fetch(url, { cache: 'no-store' });
      if(!res.ok) throw new Error('Erro ao carregar o .bib');
      const txt = await res.text();
      pre.textContent = txt.trim();
      downloadLink.href = url;
      showModal();
    }catch(err){
      pre.textContent = 'Não foi possível carregar este BibTeX.';
      showModal();
      console.error(err);
    }
  }

  function showModal(){
    modal.style.display = 'block';
    modal.setAttribute('aria-hidden', 'false');
  }
  function closeModal(){
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
    pre.textContent = '';
    currentBibUrl = null;
    downloadLink.removeAttribute('href');
  }

  // Delegação de clique: todos os .bibtex-btn
  document.addEventListener('click', function(e){
    const btn = e.target.closest('.bibtex-btn');
    if(btn && btn.dataset.bibUrl){
      e.preventDefault();
      openFromUrl(btn.dataset.bibUrl);
    }
    if(e.target === modal) closeModal(); // clicar no fundo escuro
  });

  closeBtn.addEventListener('click', closeModal);
  document.addEventListener('keydown', function(e){ if(e.key==='Escape') closeModal(); });

  copyBtn.addEventListener('click', async function(){
    try{
      await navigator.clipboard.writeText(pre.textContent);
      copyBtn.textContent = 'Copiado!';
      setTimeout(()=> copyBtn.textContent = 'Copiar', 1200);
    }catch(err){
      console.error('Falha ao copiar', err);
    }
  });
})();
</script>
