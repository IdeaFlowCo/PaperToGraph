'use strict';
(() => {
    const queryInput = document.querySelector("#query-input");
    const searchButton = document.querySelector("#btn-search");
    const searchSpinner = document.querySelector("#search-loading-spinner");
    const genericErrorMsg = document.querySelector('#generic-error-msg');
    const answerOutput = document.querySelector("#answer-output");
    const notesOutput = document.querySelector("#notes-output");
    const sourcesOutput = document.querySelector("#sources-output");

    const buildSearchBody = () => {
        const query = queryInput.value;
        const body = {
            'query': query,
        };

        return body;
    }

    const handleSearchClick = async () => {
        // Hide any messages from previous attempts
        genericErrorMsg.classList.add('hidden');

        // Disable submit button
        searchButton.disabled = true;

        // Show spinner
        searchSpinner.classList.remove('hidden');

        const response = await fetch('jack-search', {
            method: 'POST',
            mode: 'cors',
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(buildSearchBody())
        });

        try {
            const parsedResponse = await response.json();
            console.log('Received search response:', parsedResponse);

            const answer = parsedResponse.result?.answer;
            answerOutput.innerText = answer;

            let resourcesText = '';
            for (const key in parsedResponse.result?.resources) {
                resourcesText += key + ': ' + parsedResponse.result?.resources[key] + '\n';
            }
            // const resources = parsedResponse.result?.resources;
            notesOutput.innerText = resourcesText;

            const citationsBySource = {};
            sourcesOutput.innerHTML = '';
            for (const citationNumber in parsedResponse.result?.metadata) {
                const metadata = parsedResponse.result?.metadata[citationNumber];
                if (!metadata || !metadata.source || !metadata.title) {
                    continue;
                }
                if (!citationsBySource[metadata.source]) {
                    citationsBySource[metadata.source] = { '_citations': [], '_title': metadata.title };
                }
                citationsBySource[metadata.source]['_citations'].push(citationNumber);
            }
            for (const sourceUrl in citationsBySource) {
                const source = citationsBySource[sourceUrl];
                const title = source._title.endsWith('.txt') ? source._title.slice(0, -4) : source._title;
                const citations = source._citations.join(', ');
                const sourceLinkEl = document.createElement('a');
                sourceLinkEl.textContent = `[${citations}] ${title}`;
                sourceLinkEl.href = sourceUrl;
                sourceLinkEl.target = '_blank';
                sourcesOutput.appendChild(sourceLinkEl);
            }


            searchButton.disabled = false;
            searchSpinner.classList.add('hidden');
        } catch (e) {
            console.error(e);
            genericErrorMsg.classList.remove('hidden');
            // Re-enable search button so user can try again
            searchButton.disabled = false;
            searchSpinner.classList.add('hidden');
        }
    };
    searchButton.addEventListener('click', handleSearchClick);
})();