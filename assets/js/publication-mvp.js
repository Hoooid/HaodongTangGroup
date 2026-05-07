(function () {
  function onReady(callback) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback);
    } else {
      callback();
    }
  }

  function publicationValue(item, metric) {
    const attr = metric === 'impact' ? 'data-pub-impact' : metric === 'citations' ? 'data-pub-citations' : 'data-pub-year';
    const raw = item.getAttribute(attr);
    if (raw === null || raw === '') return null;
    const value = Number.parseFloat(raw);
    return Number.isFinite(value) ? value : null;
  }

  function setSortValues(grid, metric, direction) {
    grid.querySelectorAll('.isotope-item').forEach((item) => {
      const value = publicationValue(item, metric);
      const sortValue = value === null ? Number.MAX_SAFE_INTEGER : direction === 'asc' ? value : -value;
      item.setAttribute('data-sort-current', String(sortValue));
    });
  }

  function applyPublicationSort(grid, keySelect, directionSelect) {
    if (!window.jQuery) return;
    const $grid = window.jQuery(grid);
    if (!$grid.data('isotope')) return;

    setSortValues(grid, keySelect.value, directionSelect.value);
    $grid.isotope({
      getSortData: {
        current: function (itemElem) {
          const value = Number.parseFloat(itemElem.getAttribute('data-sort-current'));
          return Number.isFinite(value) ? value : Number.MAX_SAFE_INTEGER;
        },
      },
      sortBy: 'current',
      sortAscending: true,
    });
  }

  function initPublicationSort() {
    const grid = document.querySelector('#container-publications');
    const keySelect = document.querySelector('.publication-sort-key');
    const directionSelect = document.querySelector('.publication-sort-direction');
    if (!grid || !keySelect || !directionSelect) return;

    const sort = () => applyPublicationSort(grid, keySelect, directionSelect);
    keySelect.addEventListener('change', sort);
    directionSelect.addEventListener('change', sort);
    sort();
  }

  function initCitationCopy() {
    document.addEventListener(
      'click',
      function (event) {
        const copyButton = event.target.closest('.js-copy-cite');
        if (!copyButton) return;

        const citation = document.querySelector('#modal .modal-body code');
        if (!citation) return;

        event.preventDefault();
        event.stopImmediatePropagation();

        const status = document.querySelector('.citation-modal__status');
        navigator.clipboard
          .writeText(citation.textContent)
          .then(function () {
            if (status) status.textContent = 'Copied';
          })
          .catch(function () {
            if (status) status.textContent = 'Copy failed';
          });
      },
      true,
    );

    document.addEventListener('click', function (event) {
      if (!event.target.closest('.js-cite-modal')) return;
      const status = document.querySelector('.citation-modal__status');
      const error = document.querySelector('#modal-error');
      if (status) status.textContent = '';
      if (error) error.textContent = '';
    });
  }

  onReady(function () {
    initPublicationSort();
    initCitationCopy();
  });
})();
