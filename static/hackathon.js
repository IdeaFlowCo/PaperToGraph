'use strict';
(() => {
    const promptButton = document.querySelector("#btn-prompt-parse");
    const promptForm = document.getElementById("promptForm");
    const responseText = document.getElementById("response-text");
    const loadingSpinner = document.getElementById("query-loading");

    function preventFormSubmit(event) {
        event.preventDefault();
    }

    promptForm.addEventListener("submit", preventFormSubmit);

    const buildRequestBody = () => {
        const query = document.querySelector("#query-input").value;
        const body = {
            'query': query,
        };
        return body;
    }

    async function handlePromptClick() {
        promptButton.disabled = true;
        loadingSpinner.classList.remove("hidden");

        const response = await fetch('ask-llama', {
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
            promptButton.disabled = false;
            loadingSpinner.classList.add("hidden");

            responseText.value = parsedResponse.answer;

        } catch (e) {
            promptButton.disabled = false;
            loadingSpinner.classList.add("hidden");
            console.error(e);
        }
    }
    promptButton.addEventListener("click", handlePromptClick);


})();