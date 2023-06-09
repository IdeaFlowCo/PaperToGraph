const translateInput = document.querySelector("#input-translate");

// const translate = document.querySelector("#btn-translate");
const rawParseButton = document.querySelector("#btn-raw-parse");
const translateSpinner = document.querySelector("#translate-loading");

const translateErrorMsg = document.querySelector('#translate-error');

const translateOutput = document.querySelector("#output-translate");

const saveToNeoBtn = document.querySelector("#btn-save-to-neo");
const saveSpinner = document.querySelector('#save-loading');

const saveErrorMsg = document.querySelector('#save-error');


function buildBodyForTranslate() {
    const model_selection = document.querySelector('input[name="model-select"]:checked')
    const model = model_selection?.value ?? 'any';
    const text = translateInput.value;
    return {
      'model': model,
      'text': text,
    };
}

function showSpinnerForTranslate() {
  // Hide translate buttons
  // translate.style.display = 'none';
  rawParseButton.style.display = 'none';
  // Show spinner
  translateSpinner.style.display = 'block';
  // Disable Save to Neo4j button
 saveToNeoBtn.disabled = true;
}

function hideSpinnerForTranslate() {
  // Hide spinner
  translateSpinner.style.display = 'none';
  // Show translate buttons
  // translate.style.display = 'inline-block';
  rawParseButton.style.display = 'inline-block';
  // Re-enable Save to Neo4j button
  saveToNeoBtn.disabled = false;
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

async function handleTranslateClick() {
    translateErrorMsg.style.display = 'none';
    showSpinnerForTranslate();

    const response = await fetch('translate', {
        method: 'POST',
        mode: 'cors',
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(buildBodyForTranslate())
      });

    try {
      const parsedResponse = await response.json();
      console.log('Parsed response json:', parsedResponse);

      const output = parsedResponse.translation;
      translateOutput.innerText = JSON.stringify(output, null, "  ");

      hideSpinnerForTranslate();

    } catch (e) {
      hideSpinnerForTranslate();
      translateErrorMsg.style.display = 'block';

      console.error(e);
    }
}
// translate.addEventListener("click", handleTranslateClick);

async function handleRawParseClick() {
    translateErrorMsg.style.display = 'none';
    showSpinnerForTranslate();

    const response = await fetch('raw-parse', {
        method: 'POST',
        mode: 'cors',
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(buildBodyForTranslate())
      });

    try {
      const parsedResponse = await response.json();
      console.log('Parsed response json:', parsedResponse);

      const output = parsedResponse.translation;
      translateOutput.innerText = JSON.stringify(output, null, "  ");

      hideSpinnerForTranslate();

    } catch (e) {
      hideSpinnerForTranslate();
      translateErrorMsg.style.display = 'block';

      console.error(e);
    }
}
rawParseButton.addEventListener("click", handleRawParseClick);

async function handleSaveClick() {
  saveErrorMsg.style.display = 'none';
  showSpinnerForSave();

  const dataToPost = document.querySelector("#output-translate").innerText.trim();

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
    console.log('Parsed response json:', parsedResponse);

    hideSpinnerForSave();
  } catch (e) {
    console.error(e);
    saveErrorMsg.style.display = 'block';

    hideSpinnerForSave();
  }
}
saveToNeoBtn.addEventListener("click", handleSaveClick);


function humanByteSize(numBytes) {
  if (numBytes < 1000) {
    return '<1kB';
  }
  if (numBytes < 1000000) {
    return `${(numBytes / 1000).toFixed(1)} kB`;
  }
  return `${(numBytes / 1000000).toFixed(1)} mB`;
}

function calcInputTextLength() {
  const input = document.querySelector("#input-translate").value;
  const byteLength = input.length * 2; // 2 bytes per character for non-emoji English text
  const humanBytes = humanByteSize(byteLength);

  const textLengthLabel = document.querySelector('#text-length');
  textLengthLabel.innerText = `Text length: ${humanBytes}`
}

function calcInputWordCount() {
  const input = document.querySelector("#input-translate").value;
  const wordCount = input.trim().split(/\s+/).length;

  const wordCountLabel = document.querySelector('#word-count');
  wordCountLabel.innerText = `Word count: ${wordCount}`
}

document.addEventListener('DOMContentLoaded', function() {
  calcInputTextLength();
  calcInputWordCount();
  translateInput.addEventListener('change', calcInputTextLength);
  translateInput.addEventListener('change', calcInputWordCount);
});


const currentTheme = localStorage.getItem("theme");
if (currentTheme == "dark") {
    document.getElementById('toggleknop').innerHTML = '<i class="fas fa-sun" id="zon" style="color:#d8c658;"></i>';
    document.body.classList.add("dark-theme");
}

function changeTheme() {
    document.body.classList.toggle("dark-theme");
    
    document.getElementById('toggleknop').innerHTML = '<i class="fas fa-moon" id="maan" style="color:#737eac;"></i>';

    let theme = "light";
    if (document.body.classList.contains("dark-theme")) {
        document.getElementById('toggleknop').innerHTML = '<i class="fas fa-sun" id="zon" style="color:#d8c658;"></i>';
        theme = "dark";
    }
    localStorage.setItem("theme", theme);
}
