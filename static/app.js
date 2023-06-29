const translateInput = document.querySelector("#input-translate");

const overridePromptCheckbox = document.querySelector('#override-prompt');
const overridePromptInput = document.querySelector('#prompt-override-text');

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
  const body = {
    'model': model,
    'text': text,
  };
  if (overridePromptCheckbox.checked) {
    body['prompt_override'] = overridePromptInput.value;
  }
  return body;
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
    translateOutput.value = JSON.stringify(output, null, 2);

    hideSpinnerForTranslate();

  } catch (e) {
    hideSpinnerForTranslate();
    translateErrorMsg.style.display = 'block';

    console.error(e);
  }
}
rawParseButton.addEventListener("click", handleRawParseClick);


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

const setDefaultOverridePrompt = async () => {
  const response = await fetch('parse-prompt', {
    method: 'GET',
  });

  const parsedResponse = await response.json();
  overridePromptInput.value = parsedResponse['prompt'].trim();
}

const handlePromptOverrideCheck = () => {
  const checkbox = document.querySelector('#override-prompt');
  const overrideInputContainer = document.querySelector('#override-prompt-container');

  if (checkbox.checked) {
    overrideInputContainer.style.display = 'block';
    setDefaultOverridePrompt();
  } else {
    overrideInputContainer.style.display = 'none';
  }
};

document.addEventListener('DOMContentLoaded', function () {
  overridePromptCheckbox.addEventListener('change', handlePromptOverrideCheck);
  translateInput.value = translateInput.value.trim();
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
