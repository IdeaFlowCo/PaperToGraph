'use strict';
(() => {
    // const translate = document.querySelector("#btn-translate");
    const rawParseButton = document.querySelector("#btn-raw-parse");
    
    const saveTextInput = document.querySelector("#output-translate");
    
    const saveToNeoBtn = document.querySelector("#btn-save-to-neo");
    const saveSpinner = document.querySelector('#save-loading');
    
    const saveInputErrorMsg = document.querySelector('#save-input-error');
    const saveErrorMsg = document.querySelector('#save-error');
    const saveSuccessMsg = document.querySelector('#save-success'); 
    
    
    function hideMessages() {
        saveErrorMsg.style.display = 'none';
        saveInputErrorMsg.style.display = 'none';
        saveTextInput.style.removeProperty('border-color');
        saveSuccessMsg.style.display = 'none';
    }
    
    function showSpinnerForSave() {
        // Hide save button
        // translate.style.display = 'none';
        saveToNeoBtn.style.display = 'none';
        // Show spinner
        saveSpinner.style.display = 'block';
        // Disable translate buttons
        // translate.disabled = true;
        rawParseButton.disabled = true;
    }
    
    function hideSpinnerForSave() {
        // Hide spinner
        saveSpinner.style.display = 'none';
        // Re-enable translate buttons
        // translate.disabled = false;
        rawParseButton.disabled = false;
        // Show Save to Neo4j button
        saveToNeoBtn.style.display = 'inline-block';
    }
    
    function isValidJson(str) {
        try {
            JSON.parse(str);
        } catch (e) {
            return false;
        }
        return true;
    }
    
    async function handleSaveClick() {
        hideMessages();
        showSpinnerForSave();
    
        const dataToPost = saveTextInput.value.trim();

        // Trim the input displayed to make it clear that we're doing that before sending
        saveTextInput.value = dataToPost;
    
        if (!isValidJson(dataToPost)) {
            saveInputErrorMsg.style.display = 'block';
            saveTextInput.style.borderColor = 'red';
            hideSpinnerForSave();
            return;
        }
    
        const response = await fetch('save-to-neo', {
            method: 'POST',
            mode: 'cors',
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                'data': dataToPost
            })
        });
    
        try {
            const parsedResponse = await response.json();
            console.log('Received save data response:', parsedResponse);
            hideSpinnerForSave();

            if (response.ok) {
                saveSuccessMsg.style.display = 'block';
            } else {
                saveErrorMsg.style.display = 'block';
            }
        } catch (e) {
            console.error(e);
            saveErrorMsg.style.display = 'block';
    
            hideSpinnerForSave();
        }
    }
    saveToNeoBtn.addEventListener("click", handleSaveClick);    
})();
