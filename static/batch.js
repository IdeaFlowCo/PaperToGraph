'use strict';
(() => {
    const dataSourceInput = document.querySelector('#data-source');
    const jobTypeInputs = document.querySelectorAll('input[name="job-type"]');
    const parseJobControls = document.querySelector('#parse-job-controls');
    const saveJobControls = document.querySelector('#save-job-controls');
    const submitJobButton = document.querySelector('#btn-submit-job');
    const cancelJobButton = document.querySelector('#btn-cancel-job');

    const handleJobTypeChange = () => {
        const selectedJobType = document.querySelector('input[name="job-type"]:checked').value;
        if (selectedJobType === 'parse') {
            parseJobControls.style.display = 'block';
            saveJobControls.style.display = 'none';
        } else if (selectedJobType === 'save') {
            parseJobControls.style.display = 'none';
            saveJobControls.style.display = 'block';
        }
        submitJobButton.disabled = false;
    }
    jobTypeInputs.forEach((input) => input.addEventListener('change', handleJobTypeChange));

    // Extra controls for overriding parse job parameters
    const dryRunCheckbox = document.querySelector("#dry-run");
    const overrideParseOutput = document.querySelector("#override-parse-output");

    // Extra controls for overriding save job parameters
    const overrideNeoUri = document.querySelector("#override-neo-uri");
    const overrideNeoUser = document.querySelector("#override-neo-user");
    const overrideNeoPass = document.querySelector("#override-neo-pass");

    const makeOverrideListener = (checkboxId, overrideInputId) =>
        () => {
            const checkbox = document.querySelector(`#${checkboxId}`);
            const overrideInputContainer = document.querySelector(`#${overrideInputId}`);

            if (checkbox.checked) {
                overrideInputContainer.style.display = 'block';
            } else {
                overrideInputContainer.style.display = 'none';
            }
        };

    overrideParseOutput.addEventListener('change', makeOverrideListener('override-parse-output', 'override-parse-output-container'));
    overrideNeoUri.addEventListener('change', makeOverrideListener('override-neo-uri', 'override-neo-uri-container'));
    overrideNeoUser.addEventListener('change', makeOverrideListener('override-neo-user', 'override-neo-user-container'));
    overrideNeoPass.addEventListener('change', makeOverrideListener('override-neo-pass', 'override-neo-pass-container'));


    const buildSubmitBody = () => {
        const dataSource = dataSourceInput.value;
        const jobType = document.querySelector('input[name="job-type"]:checked').value;
        const model = document.querySelector('input[name="model-select"]:checked')?.value ?? 'any';
        const body = {
            'job_type': jobType,
            'model': model,
            'data_source': dataSource,
        };

        const overrides = {};
        if (jobType === 'parse') {
            if (dryRunCheckbox.checked) {
                overrides['dry_run'] = true;
            }
            if (overrideParseOutput.checked) {
                overrides['output_uri'] = document.querySelector('#parse-output-uri').value;
            }
        }
        if (overrideNeoUri.checked) {
            overrides['neo_uri'] = document.querySelector('#neo-uri').value;
        }
        if (overrideNeoUser.checked) { 
            overrides['neo_user'] = document.querySelector('#neo-user').value;
        }
        if (overrideNeoPass.checked) {
            overrides['neo_pass'] = document.querySelector('#neo-pass').value;
        }

        return Object.assign({}, body, overrides);
    }

    const jobLogs = document.querySelector('#job-logs');
    let jobLogEventStream = null;
    const streamJobLogs = () => {
        jobLogEventStream = new EventSource('batch-log');
        jobLogEventStream.onmessage = (event) => {
            console.log(event);
            const eventData = event.data.trim();
            if (eventData === 'done') {
                jobLogEventStream.close();
                return;
            }
            if (eventData != 'nodata') {
                jobLogs.innerHTML += eventData + '<br>';
            }
        }
    }

    const inputErrorMsg = document.querySelector('#input-error-msg');
    const genericErrorMsg = document.querySelector('#generic-error-msg');
    const successMsg = document.querySelector('#success-msg');


    const handleSubmitClick = async () => {
        // Hide any messages from previous attempts
        inputErrorMsg.classList.add('hidden');
        genericErrorMsg.classList.add('hidden');
        successMsg.classList.add('hidden');

        // Disable submit button
        submitJobButton.disabled = true;

        const response = await fetch('new-batch-job', {
            method: 'POST',
            mode: 'cors',
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(buildSubmitBody())
        });
        
        try {
            const parsedResponse = await response.json();
            console.log('Received submit response:', parsedResponse);

            if (response.ok) {
                successMsg.classList.remove('hidden');
                jobInfo.classList.remove('hidden');
                cancelJobButton.disabled = false;
                streamJobLogs();
            } else {
                inputErrorMsg.classList.remove('hidden');
                // Re-enable submit button so user can try again
                submitJobButton.disabled = false;
            }
        } catch (e) {
            console.error(e);
            genericErrorMsg.classList.remove('hidden');
            // Re-enable submit button so user can try again
            submitJobButton.disabled = false;
        }
    };
    submitJobButton.addEventListener('click', handleSubmitClick);


    const handleCancelClick = async () => {
        // Disable cancel button
        cancelJobButton.disabled = true;

        const response = await fetch('cancel-batch-job', {
            method: 'POST',
            mode: 'cors',
            headers: {
                "Content-Type": "application/json",
            },
        });

        try {
            const parsedResponse = await response.json();
            console.log('Received cancel response:', parsedResponse);

            if (response.ok) {
                // successMsg.classList.remove('hidden');
                jobInfo.classList.add('hidden');
                if (jobLogEventStream) {
                    jobLogEventStream.close();
                }
                jobLogEventStream = null;
                // streamJobLogs();
            } else {
                inputErrorMsg.classList.remove('hidden');
                // Re-enable submit button so user can try again
                submitJobButton.disabled = false;
            }
        } catch (e) {
            console.error(e);
            genericErrorMsg.classList.remove('hidden');
            // Re-enable submit button so user can try again
            submitJobButton.disabled = false;
        }
    }
    cancelJobButton.addEventListener('click', handleCancelClick);

    const newJobControls = document.querySelector('#new-job-controls');
    const jobInfo = document.querySelector('#job-info');
    const jobStatusSpinner = document.querySelector('#job-status-spinner');

    const checkJobRunning = async () => {
        // Hide controls, show spinner while checking status
        newJobControls.classList.add('hidden');
        jobInfo.classList.add('hidden');
        jobStatusSpinner.classList.remove('hidden');

        const response = await fetch('batch-status', {
            method: 'GET'
        });

        try {
            const parsedResponse = await response.json();
            console.log('Received status response:', parsedResponse);

            if (parsedResponse['status'] === 'running') {
                // Hide spinner, show job info
                jobStatusSpinner.classList.add('hidden');
                newJobControls.classList.remove('hidden');
                jobInfo.classList.remove('hidden');
                cancelJobButton.disabled = false;
                streamJobLogs();
            } else {
                // Hide spinner, show new job controls
                jobStatusSpinner.classList.add('hidden');
                newJobControls.classList.remove('hidden');
            }
        } catch (e) {
            console.error(e);
            genericErrorMsg.style.display = 'block';
        }
    };
    document.addEventListener('DOMContentLoaded', checkJobRunning);
})();
