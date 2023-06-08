var translate = document.querySelector("#btn-translate");
var raw_parse_button = document.querySelector("#btn-raw-parse");
var input_translate = document.querySelector("#input-translate")
var output_translate = document.querySelector("#output-translate")
var loading = document.querySelector("#loading");

// mock server
// var url = "https://lessonfourapi.tanaypratap.repl.co/translate/yoda.json"


// actual server
var url = "post"

function buildUrlForGetRequest(url) {
    const model_selection = document.querySelector('input[name="model-select"]:checked')
    model = model_selection?.value ?? 'any';
    return url + "?" + "model=" + model + "&text=" + input_translate.value
}

function buildBodyForPost() {
    const model_selection = document.querySelector('input[name="model-select"]:checked')
    const model = model_selection?.value ?? 'any';
    const text = input_translate.value;
    return {
      'model': model,
      'text': text,
    };
}

async function handleTranslateClick() {
    // Show spinner
    loading.style.display = 'block';
    // Hide buttons
    translate.style.display = 'none';
    raw_parse_button.style.display = 'none';

    const response = await fetch(url, {
        method: 'POST',
        mode: 'cors',
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(buildBodyForPost())
      });

    let bytesReceived = 0;
    let responseBody = '';

    try {
      for await (let chunk of response.body) {
        console.log(`Received ${chunk.length} bytes`);
        bytesReceived += chunk.length;
        chunk = String.fromCharCode(...chunk);
        console.log(`Chunk: ${chunk}`);
        responseBody += chunk;
      }
      
      const parsedResponse = JSON.parse(responseBody);
      console.log('Parsed response json:', parsedResponse);

      const output_text = parsedResponse.translation;
      output_translate.innerText = output_text.trim(); // For some reason the response comes back with leading \n's

      // Hide spinner
      loading.style.display = 'none';
      // Show buttons
      translate.style.display = 'inline-block';
      raw_parse_button.style.display = 'inline-block';

    } catch (e) {
      // Hide spinner
       loading.style.display = 'none';
       // Show buttons
       translate.style.display = 'inline-block';
       raw_parse_button.style.display = 'inline-block';

       console.error(e);
       alert("Something wrong with the server. Please try again later.");
    }
}
translate.addEventListener("click", handleTranslateClick);

async function handleRawParseClick() {
    // Show spinner
    loading.style.display = 'block';
    // Hide buttons
    translate.style.display = 'none';
    raw_parse_button.style.display = 'none';

    const response = await fetch('raw-parse', {
        method: 'POST',
        mode: 'cors',
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(buildBodyForPost())
      });

    let bytesReceived = 0;
    let responseBody = '';

    try {
      for await (let chunk of response.body) {
        console.log(`Received ${chunk.length} bytes`);
        bytesReceived += chunk.length;
        chunk = String.fromCharCode(...chunk);
        console.log(`Chunk: ${chunk}`);
        responseBody += chunk;
      }
      
      const parsedResponse = JSON.parse(responseBody);
      console.log('Parsed response json:', parsedResponse);

      const output_text = parsedResponse.translation;
      output_translate.innerText = output_text.trim(); // For some reason the response comes back with leading \n's

      // Hide spinner
      loading.style.display = 'none';
      // Show buttons
      translate.style.display = 'inline-block';
      raw_parse_button.style.display = 'inline-block';

    } catch (e) {
      // Hide spinner
       loading.style.display = 'none';
       // Show buttons
       translate.style.display = 'inline-block';
       raw_parse_button.style.display = 'inline-block';

       console.error(e);
       alert("Something wrong with the server. Please try again later.");
    }
}
raw_parse_button.addEventListener("click", handleRawParseClick);


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
  input_translate.addEventListener('change', calcInputTextLength);
  input_translate.addEventListener('change', calcInputWordCount);
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
