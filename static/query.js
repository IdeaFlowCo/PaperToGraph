'use strict';
(() => {
    const queryInput = document.querySelector("#query-input");
    const searchButton = document.querySelector("#btn-search");
    const searchSpinner = document.querySelector("#search-loading-spinner");
    const genericErrorMsg = document.querySelector('#generic-error-msg');
    const answerOutput = document.querySelector("#answer-output");
    const referencesOutput = document.querySelector("#references-output");
    const sourcesOutput = document.querySelector("#sources-output");

    const buildSearchBody = () => {
        const query = queryInput.value;
        const body = {
            'query': query,
        };

        return body;
    }

    const answerWithCitationsInline = (parsedResponse) => {
        const answer = parsedResponse.answer;
        const resourceIds = parsedResponse.resource_ids;

        // Regular expression to match citations in the answer
        const citationRegex = /\[(\d+)\]/g;

        // Replace citations in the answer with links to corresponding sources
        const modifiedAnswer = answer.replace(citationRegex, (match, citationNumber) => {
            const sourceUrl = resourceIds[citationNumber];
            if (sourceUrl) {
                return `<a href="${sourceUrl}" target="_blank">[${citationNumber}]</a>`;
            }
            // If source URL not found, return the original match
            return match;
        });

        return modifiedAnswer;
    }

    const handleSearchClick = async () => {
        // Hide any messages from previous attempts
        genericErrorMsg.classList.add('hidden');

        // Disable submit button
        searchButton.disabled = true;

        // Show spinner
        searchSpinner.classList.remove('hidden');

        const response = await fetch('query-simon', {
            method: 'POST',
            mode: 'cors',
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(buildSearchBody())
        });

        try {
            const parsed = await response.json();
            console.log('Received search response:', parsed);

            const answer = answerWithCitationsInline(parsed);
            answerOutput.innerHTML = answer;

            let resourcesText = '';
            const citationsBySource = {};
            for (const [source, references] of Object.entries(parsed.resource_references)) {
                citationsBySource[source] = { 'title': '', 'citations': [] };
                for (const [refNum, reference] of Object.entries(references)) {
                    if (refNum === '_hash') continue;

                    const refLink = document.createElement('a');
                    refLink.textContent = `[${refNum}]`;
                    refLink.href = reference.metadata.source;
                    refLink.target = '_blank';

                    resourcesText += `${refLink.outerHTML}: ${reference.text}<br>`;

                    let title = reference.metadata.title
                    title = title.endsWith('.txt') ? title.slice(0, -4) : title;
                    citationsBySource[source]['title'] = title;
                    citationsBySource[source]['citations'].push(refNum);
                }
            }
            referencesOutput.innerHTML = resourcesText;

            sourcesOutput.innerHTML = '';
            for (const sourceUrl in citationsBySource) {
                const source = citationsBySource[sourceUrl];
                const sourceLinkEl = document.createElement('a');
                sourceLinkEl.textContent = `[${source.citations.join(', ')}] ${source.title}`;
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