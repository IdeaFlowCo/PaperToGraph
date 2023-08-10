'use strict';
(() => {
    const searchInput = document.querySelector("#search-input");
    const searchButton = document.querySelector("#btn-search");

    const searchSpinner = document.querySelector("#search-loading-spinner");
    const searchErrorMsg = document.querySelector('#search-error-msg');

    const matchingPapersLabel = document.querySelector("#matching-papers-label");
    const searchResultsList = document.querySelector("#search-results-list");
    const searchResultsPlaceholder = document.querySelector("#search-results-placeholder");
    const searchResultsEmpty = document.querySelector("#search-results-empty");

    const searchPaginationControls = document.querySelector("#search-pagination-controls");
    const searchResultsPagination = document.querySelector("#search-results-pagination");
    const searchResultsPrevPage = document.querySelector("#search-results-prev-page");
    const searchResultsNextPage = document.querySelector("#search-results-next-page");
    const searchResultsFirstPage = document.querySelector("#search-results-first-page");
    const searchResultsLastPage = document.querySelector("#search-results-last-page");

    const addToListButton = document.querySelector("#btn-add-to-list");

    const newBatchList = document.querySelector("#new-batch-list");
    const newBatchCreateButton = document.querySelector("#btn-new-batch-set");
    const newBatchDedupeButton = document.querySelector("#btn-new-batch-dedupe");

    const newBatchSpinner = document.querySelector("#new-batch-loading-spinner");

    const newBatchErrorMsg = document.querySelector('#new-batch-error-msg');
    const newBatchBadFilesMsg = document.querySelector('#new-batch-bad-files-msg');
    const newBatchBadFilesList = document.querySelector('#new-batch-bad-files-list');

    const newBatchSuccessMsg = document.querySelector('#new-batch-success-msg');
    const newBatchUriHolder = document.querySelector('#new-batch-uri');

    const buildSearchRequestBody = () => {
        const query = searchInput.value;
        const body = {
            'query': query,
        };

        return body;
    }

    let filePages = [];
    let curFilePage = 0;
    const FILES_PER_PAGE = 10;
    const clearSearchResults = () => {
        // Hide any error messages from any previous requests
        searchResultsEmpty.classList.add('hidden');
        searchErrorMsg.classList.add('hidden');
        newBatchErrorMsg.classList.add('hidden');

        // Clear any previous results and hide the list
        searchResultsList.innerHTML = '';
        searchResultsList.classList.add('hidden');

        // Ensure placeholder is being shown again
        searchResultsPlaceholder.classList.remove('hidden');

        filePages = [];
        curFilePage = 0;
        matchingPapersLabel.textContent = 'Matching papers';
    };

    const disableButtons = () => {
        searchButton.disabled = true;
        addToListButton.disabled = true;
        newBatchCreateButton.disabled = true;
        newBatchDedupeButton.disabled = true;
    };

    const resetButtonStates = () => {
        searchButton.disabled = false;
        addToListButton.disabled = !searchResultsList.innerHTML.trim();
        newBatchCreateButton.disabled = !newBatchList.innerHTML.trim();
        newBatchDedupeButton.disabled = !newBatchList.innerHTML.trim();
    }

    const displayCurFilePage = () => {
        searchResultsList.innerHTML = '';
        for (const file of filePages[curFilePage]) {
            const pmcId = file.pmcId;
            const articleType = file.articleType;
            const title = file.title;
            const doi = file.doi;
            const path = file.path;
            const resultLiEl = document.createElement('li');
            const pmcIdEl = document.createElement('span');
            pmcIdEl.classList.add('pmc-id');
            pmcIdEl.textContent = pmcId;
            resultLiEl.appendChild(pmcIdEl);
            const articleTypeEl = document.createElement('span');
            articleTypeEl.classList.add('article-type');
            articleTypeEl.textContent = articleType;
            resultLiEl.appendChild(articleTypeEl);
            const titleEl = document.createElement('span');
            titleEl.classList.add('article-title');
            titleEl.textContent = title;
            titleEl.title = title;
            resultLiEl.appendChild(titleEl);
            // const doiEl = document.createElement('span');
            // doiEl.textContent = doi;
            // resultLiEl.appendChild(doiEl);
            // const pathEl = document.createElement('span');
            // pathEl.classList.add('article-path');
            // pathEl.textContent = path;
            // resultLiEl.appendChild(pathEl);
            searchResultsList.appendChild(resultLiEl);
        }

        if (filePages.length > 1) {
            rebuildPaginationList();
            searchPaginationControls.classList.remove('hidden');
        } else {
            searchPaginationControls.classList.add('hidden');
        }
    }

    const buildElipsesPageItemEl = () => {
        const pageItemEl = document.createElement('li');
        pageItemEl.classList.add('page-item');
        pageItemEl.classList.add('disabled');
        const pageLinkEl = document.createElement('a');
        pageLinkEl.classList.add('page-link');
        pageLinkEl.textContent = '...';
        pageLinkEl.href = '#';
        pageItemEl.appendChild(pageLinkEl);
        return pageItemEl;
    }

    const buildPageItemEl = (pageNum) => {
        const pageItemEl = document.createElement('li');
        pageItemEl.classList.add('page-item');
        const pageLinkEl = document.createElement('a');
        pageLinkEl.classList.add('page-link');
        pageLinkEl.textContent = pageNum + 1;
        pageLinkEl.href = '#';
        if (pageNum === curFilePage) {
            pageLinkEl.classList.add('active');
        } else {
            pageLinkEl.addEventListener('click', () => {
                curFilePage = pageNum;
                displayCurFilePage();
            });
        }
        pageItemEl.appendChild(pageLinkEl);
        return pageItemEl
    }

    const rebuildPaginationList = () => {
        searchResultsPagination.innerHTML = '';

        if (curFilePage > 0) {
            searchResultsPrevPage.classList.remove('disabled');
            searchResultsFirstPage.classList.remove('disabled');
        }
        else {
            searchResultsPrevPage.classList.add('disabled');
            searchResultsFirstPage.classList.add('disabled');
        }
        searchResultsPagination.appendChild(searchResultsPrevPage);

        if (curFilePage > 2) {
            searchResultsFirstPage.classList.remove('disabled');
            const elipsesItem = buildElipsesPageItemEl();
            searchResultsPagination.appendChild(elipsesItem);
        }
        for (let i = Math.max(0, curFilePage - 2); i < Math.min(filePages.length, curFilePage + 3); i++) {
            const pageItemEl = buildPageItemEl(i);
            searchResultsPagination.appendChild(pageItemEl);
        }
        if (filePages.length - curFilePage > 3) {
            const elipsesItem = buildElipsesPageItemEl();
            searchResultsPagination.appendChild(elipsesItem);
        }

        if (curFilePage < filePages.length - 1) {
            searchResultsNextPage.classList.remove('disabled');
            searchResultsLastPage.classList.remove('disabled');
        }
        else {
            searchResultsNextPage.classList.add('disabled');
            searchResultsLastPage.classList.add('disabled');
        }
        searchResultsPagination.appendChild(searchResultsNextPage);
    }

    searchResultsPrevPage.addEventListener('click', () => {
        if (curFilePage == 0) return;
        curFilePage -= 1;
        displayCurFilePage();
    });
    searchResultsFirstPage.addEventListener('click', () => {
        if (curFilePage == 0) return;
        curFilePage = 0;
        displayCurFilePage();
    });
    searchResultsNextPage.addEventListener('click', () => {
        if (curFilePage == filePages.length - 1) return;
        curFilePage += 1;
        displayCurFilePage();
    });
    searchResultsLastPage.addEventListener('click', () => {
        if (curFilePage == filePages.length - 1) return;
        curFilePage = filePages.length - 1;
        displayCurFilePage();
    });

    const displayFileResults = (files) => {
        searchPaginationControls.classList.add('hidden');
        filePages = [];
        for (let i = 0; i < files.length; i += FILES_PER_PAGE) {
            filePages.push(files.slice(i, i + FILES_PER_PAGE));
        }
        curFilePage = 0;
        displayCurFilePage();

        searchResultsList.classList.remove('hidden');
    }

    searchButton.addEventListener('click', async () => {
        clearSearchResults();
        disableButtons();

        searchSpinner.classList.remove('hidden');

        const response = await fetch('doc-search', {
            method: 'POST',
            mode: 'cors',
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(buildSearchRequestBody())
        });

        try {
            const parsedResponse = await response.json();
            console.log('Received search response:', parsedResponse);

            searchResultsPlaceholder.classList.add('hidden');
            searchSpinner.classList.add('hidden');

            let foundFiles = parsedResponse.files;
            if (!foundFiles || !foundFiles.length) {
                searchResultsEmpty.classList.remove('hidden');
                resetButtonStates();
                return;
            }
            foundFiles = foundFiles.map(file => {
                // PMC ID and Path will always be provided; other fields may be missing
                const pmcId = file.pmc_id;
                const path = file.path;

                const title = file.title || '[Title not found]';
                const articleType = file.article_type || '[Type not found]';
                const doi = file.doi || '[DOI not found]';
                return { pmcId, path, title, articleType, doi };
            });
            foundFiles = foundFiles.sort(
                // Sort by paper ID; first by length, then alphanumerically (so that PMC10* IDs come after PMC9* IDs)
                (a, b) => a.pmcId.length != b.pmcId.length ? a.pmcId.length - b.pmcId.length : a.pmcId.localeCompare(b.pmcId)
            );
            matchingPapersLabel.textContent = `${foundFiles.length} papers found`;
            displayFileResults(foundFiles);
            resetButtonStates();
        } catch (e) {
            console.error(e);
            searchSpinner.classList.add('hidden');
            searchErrorMsg.classList.remove('hidden');
            resetButtonStates();
        }
    })

    const trimNewBatchList = () => {
        const newBatchItems = newBatchList.innerHTML.split('<br>')
            .filter((row) => !!row) // Remove empty rows
            .map((row) => row.trim()) // Trim whitespace from every row
            ;
        newBatchList.innerHTML = newBatchItems.join('<br>');
    };

    addToListButton.addEventListener('click', async () => {
        disableButtons();
        let newFilesString = '';
        for (const filePage of filePages) {
            for (const file of filePage) {
                newFilesString += file.path + '\t' + file.title + '<br>';
            }
        }
        newBatchList.innerHTML = newBatchList.innerHTML + '<br>' + newFilesString;
        trimNewBatchList();
        resetButtonStates();
    });

    newBatchList.addEventListener('blur', async () => {
        trimNewBatchList();
        resetButtonStates();
    });

    const buildNewBatchRequestBody = () => {
        const batchItems = newBatchList.innerHTML.split('<br>').map((row) => {
            if (row.indexOf('\t') == -1) return row.trim();
            const path = row.split('\t')[0];
            return path.trim()
        });
        const body = {
            'files': batchItems,
        };

        return body;
    }

    newBatchCreateButton.addEventListener('click', async () => {
        disableButtons();

        newBatchErrorMsg.classList.add('hidden');
        newBatchBadFilesMsg.classList.add('hidden');
        newBatchSuccessMsg.classList.add('hidden');

        newBatchSpinner.classList.remove('hidden');


        const response = await fetch('new-doc-set', {
            method: 'POST',
            mode: 'cors',
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(buildNewBatchRequestBody())
        });

        try {
            const parsedResponse = await response.json();
            console.log('Received create batch set response:', parsedResponse);

            searchResultsPlaceholder.classList.add('hidden');
            newBatchSpinner.classList.add('hidden');

            if (!!parsedResponse.error) {
                console.error('Error from server when creating new batch set:', parsedResponse.error);
                if (parsedResponse.error === 'Unknown files') {
                    newBatchBadFilesList.innerText = parsedResponse.detail.join('\n');
                    newBatchBadFilesMsg.classList.remove('hidden');
                } else {
                    newBatchErrorMsg.classList.remove('hidden');
                }
            } else if (!!parsedResponse.uri) {
                newBatchUriHolder.textContent = parsedResponse.uri;
                newBatchSuccessMsg.classList.remove('hidden');
            } else {
                console.error('Unexpected response:', parsedResponse);
                newBatchErrorMsg.classList.remove('hidden');
            }
            resetButtonStates();
        } catch (e) {
            console.error('Error from server when creating new batch set:', e);
            newBatchSpinner.classList.add('hidden');
            newBatchErrorMsg.classList.remove('hidden');
            resetButtonStates();
        }
    });

    newBatchDedupeButton.addEventListener('click', async () => {
        disableButtons();
        const batchItems = newBatchList.innerHTML.split('<br>')
            .map((row) => row.trim())
            .filter((item) => !!item);
        // Dedupe then sort
        newBatchList.innerHTML = [...new Set(batchItems)].sort().join('<br>');
        resetButtonStates();
    });

    newBatchUriHolder.addEventListener('click', () => {
        // Select the full URI text when the user clicks on it
        const range = document.createRange();
        range.selectNode(newBatchUriHolder);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
    });
})();