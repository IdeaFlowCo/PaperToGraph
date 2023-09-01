'use strict';
(() => {
    const searchButton = document.getElementById("btn-search");
    const responseText = document.getElementById("response-text");
    const loadingSpinner = document.getElementById("query-loading");

    const buildRequestBody = () => {
        const query = document.querySelector("#query-input").value;
        const model = document.querySelector('input[name="model-select"]:checked').value;
        const body = {
            'query': query,
            'llm': model,
        };
        return body;
    }

    async function handlePromptClick() {
        searchButton.disabled = true;
        loadingSpinner.classList.remove("hidden");

        const response = await fetch('ask-llm', {
            method: 'POST',
            mode: 'cors',
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(buildRequestBody())
        });

        try {
            const parsedResponse = await response.json();
            console.log('Parsed response json:', parsedResponse);
            searchButton.disabled = false;
            loadingSpinner.classList.add("hidden");

            responseText.value = parsedResponse.answer;

        } catch (e) {
            searchButton.disabled = false;
            loadingSpinner.classList.add("hidden");
            console.error(e);
        }
    }
    searchButton.addEventListener("click", handlePromptClick);
})();