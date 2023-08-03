'use strict';
(() => {
    const searchInput = document.querySelector("#search-input");
    const searchButton = document.querySelector("#btn-search");

    const searchSpinner = document.querySelector("#search-loading-spinner");
    const searchErrorMsg = document.querySelector('#search-error-msg');

    const searchResultsList = document.querySelector("#search-results-list");
    const searchResultsPlaceholder = document.querySelector("#search-results-placeholder");
    const searchResultsEmpty = document.querySelector("#search-results-empty");

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
        newBatchCreateButton.disabled = !newBatchList.value;
        newBatchDedupeButton.disabled = !newBatchList.value;
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

            const foundFiles = parsedResponse.files;
            if (!foundFiles || !foundFiles.length) {
                searchResultsEmpty.classList.remove('hidden');
                resetButtonStates();
                return;
            }

            for (const file of foundFiles) {
                const title = file.title;
                const path = file.path;
                const resultLiEl = document.createElement('li');
                resultLiEl.dataset.title = title;
                resultLiEl.dataset.path = path;
                resultLiEl.textContent = `${title} \u2014 ${path}`;
                searchResultsList.appendChild(resultLiEl);
            }

            searchResultsList.classList.remove('hidden');
            resetButtonStates();
        } catch (e) {
            console.error(e);
            searchSpinner.classList.add('hidden');
            searchErrorMsg.classList.remove('hidden');
            resetButtonStates();
        }
    });

    addToListButton.addEventListener('click', async () => {
        disableButtons();
        for (const resultEl of searchResultsList.children) {
            newBatchList.value = (newBatchList.value.trim() + '\n' + resultEl.dataset.path).trim();
        }
        resetButtonStates();
    });

    newBatchList.addEventListener('blur', async () => {
        newBatchList.value = newBatchList.value.trim();
        resetButtonStates();
    });

    const buildNewBatchRequestBody = () => {
        const batchItems = newBatchList.value.split('\n').map((item) => item.trim());
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
        const batchItems = newBatchList.value.split('\n').map((item) => item.trim()).filter((item) => !!item);
        // Dedupe then sort; first by length, then alphanumerically (so that PMC10* IDs come after PMC9* IDs)
        newBatchList.value = [...new Set(batchItems)].sort(
            (a, b) => a.length != b.length ? a.length - b.length : a.localeCompare(b)
        ).join('\n');
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