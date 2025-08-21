window.scaleInfo = null;
window.currentImgSize = null;

window.addEventListener('DOMContentLoaded', function () {
    const urlParams = new URLSearchParams(window.location.search);
    const viewer = urlParams.get('viewer');
    const dashboardUrl = urlParams.get('dashboard');

    if (!viewer || !dashboardUrl) {
        console.log("No viewer or dashboard URL provided");
        return;
    }

    document.getElementById('dashboardButton').href = dashboardUrl;
    loadDataset(viewer);
});

document.addEventListener('keydown', function (e) {
    if (e.ctrlKey && e.key === 'd') {
        e.preventDefault();
        openROIDownload();
    }
});

function loadDataset(url) {
    document.getElementById('interface').src = url;
}

async function openROIDownload() {
    document.getElementById('roiDialog').style.display = 'flex';
    await loadDialogData();
}

function closeROIDialog() {
    document.getElementById('roiDialog').style.display = 'none';
    const axes = ['X', 'Y', 'Z'];
    axes.forEach(axis => {
        const checkbox = document.getElementById(`whole${axis}`);
        const startInput = document.getElementById(`${axis.toLowerCase()}Start`);
        const endInput = document.getElementById(`${axis.toLowerCase()}End`);

        if (checkbox) checkbox.checked = false;
        if (startInput) startInput.disabled = false;
        if (endInput) endInput.disabled = false;
    });
}

async function loadDialogData() {
    try {
        const response = await fetch('/api/layer_info');
        const data = await response.json();

        setupLayerSelect(data.layers);

        if (data.layers.length > 0) {
            const firstLayerUrl = data.layers[0].url.replace("precomputed://", "");
            await loadResolutionData(firstLayerUrl);
        }
    } catch (error) {
        console.error('Failed to load dialog data:', error);
    }
}

function setupLayerSelect(layers) {
    const layerSelect = document.getElementById('layer');
    layerSelect.innerHTML = '<option value="">Select layer...</option>';

    layers.forEach((layer, index) => {
        const option = document.createElement('option');
        option.value = layer.id;
        option.textContent = layer.id;
        option.setAttribute('url', layer.url);
        if (index === 0) option.selected = true;
        layerSelect.appendChild(option);
    });

    layerSelect.addEventListener('change', handleLayerChange);
}

async function handleLayerChange() {
    const selectedOption = this.options[this.selectedIndex];
    const layerUrl = selectedOption.getAttribute('url');

    if (layerUrl) {
        const layerUrlShort = layerUrl.replace("precomputed://", "");
        await loadResolutionData(layerUrlShort);
    } else {
        document.getElementById('resolution').innerHTML = '<option value="">Select resolution...</option>';
    }
}

async function loadResolutionData(layerUrl) {
    try {
        const response = await fetch(`${layerUrl}/info`);
        const data = await response.json();
        window.scaleInfo = data.scales;

        setupResolutionSelect(data.scales);

        if (data.scales.length > 0) {
            const imgSize = data.scales[0].size;
            window.currentImgSize = imgSize;
            await loadROIData();
        }
    } catch (error) {
        console.error('Failed to load resolution data:', error);
        document.getElementById('resolution').innerHTML = '<option value="">Select resolution</option>';
    }
}

async function loadROIData() {
    try {
        const response = await fetch('/api/roi_info');
        const data = await response.json();

        populateROIFields(data.roi, window.currentImgSize);
        setupWholeCheckboxes();
    } catch (error) {
        console.error('Failed to load roi data:', error);
    }
}

function setupWholeCheckboxes() {
    // Add event listeners for the whole checkboxes
    document.getElementById('wholeX').addEventListener('change', function () {
        handleWholeCheckbox('x', this.checked);
    });

    document.getElementById('wholeY').addEventListener('change', function () {
        handleWholeCheckbox('y', this.checked);
    });

    document.getElementById('wholeZ').addEventListener('change', function () {
        handleWholeCheckbox('z', this.checked);
    });
}

function handleWholeCheckbox(axis, isChecked) {
    if (!window.currentImgSize) return;

    const axisIndex = axis === 'x' ? 0 : axis === 'y' ? 1 : 2;
    const maxValue = window.currentImgSize[axisIndex] - 1;

    if (isChecked) {
        // Set to whole dimension
        document.getElementById(`${axis}Start`).value = 0;
        document.getElementById(`${axis}End`).value = maxValue;

        // Disable the input fields
        document.getElementById(`${axis}Start`).disabled = true;
        document.getElementById(`${axis}End`).disabled = true;
    } else {
        // Re-enable the input fields
        document.getElementById(`${axis}Start`).disabled = false;
        document.getElementById(`${axis}End`).disabled = false;
    }
}

function populateROIFields(roi, imgSize) {
    if (!roi || !imgSize) return;

    const clampValue = (value, max) => {
        if (value === undefined || value === null) return '';
        const num = Number(value);
        if (isNaN(num)) return '';
        return Math.max(0, Math.min(num, max));
    };

    const fields = [
        { id: 'xStart', value: clampValue(roi.x?.[0], imgSize[0]) },
        { id: 'xEnd', value: clampValue(roi.x?.[1], imgSize[0]) },
        { id: 'yStart', value: clampValue(roi.y?.[0], imgSize[1]) },
        { id: 'yEnd', value: clampValue(roi.y?.[1], imgSize[1]) },
        { id: 'zStart', value: clampValue(roi.z?.[0], imgSize[2]) },
        { id: 'zEnd', value: clampValue(roi.z?.[1], imgSize[2]) }
    ];

    fields.forEach(field => {
        const element = document.getElementById(field.id);
        if (element) {
            element.value = field.value;
        } else {
            console.warn(`Element with id '${field.id}' not found`);
        }
    });

    // Check if any axis is using the whole dimension and update checkboxes accordingly
    updateWholeCheckboxStates(roi, imgSize);
}

function updateWholeCheckboxStates(roi, imgSize) {
    const axes = ['x', 'y', 'z'];

    axes.forEach((axis, index) => {
        const checkbox = document.getElementById(`whole${axis.toUpperCase()}`);
        if (!checkbox) return;

        const roiAxis = roi[axis];
        if (roiAxis && roiAxis[0] === 0 && roiAxis[1] === imgSize[index]) {
            checkbox.checked = true;
            handleWholeCheckbox(axis, true);
        } else {
            checkbox.checked = false;
            handleWholeCheckbox(axis, false);
        }
    });
}

function setupResolutionSelect(scales) {
    const resolutionSelect = document.getElementById('resolution');
    resolutionSelect.innerHTML = '<option value="">Select resolution...</option>';

    if (!scales) return;

    scales.forEach(scale => {
        const option = document.createElement('option');
        option.value = scale.key;
        option.textContent = `Scale ${scale.key} (${scale.resolution.join('x')} nm)`;
        if (Number(scale.key) === 1) option.selected = true;
        resolutionSelect.appendChild(option);
    });

    resolutionSelect.addEventListener('change', updateROIForScale);
}

async function updateROIForScale() {
    try {
        const response = await fetch('/api/roi_info');
        const data = await response.json();
        const resolution = document.getElementById('resolution').value;

        if (!resolution || !window.scaleInfo) return;

        const baseScale = window.scaleInfo.find(s => s.key === '1');
        const selectedScale = window.scaleInfo.find(s => s.key === resolution);

        if (!baseScale || !selectedScale) return;

        // Update current image size for the selected scale
        window.currentImgSize = selectedScale.size;

        const scaleFactors = calculateScaleFactors(baseScale, selectedScale);
        applyScaleToROI(data.roi, scaleFactors);

        // Update whole checkboxes for the new scale
        updateWholeCheckboxesForScale();
    } catch (error) {
        console.error('Failed to load dialog data:', error);
    }
}

function updateWholeCheckboxesForScale() {
    const axes = ['x', 'y', 'z'];

    axes.forEach((axis) => {
        const checkbox = document.getElementById(`whole${axis.toUpperCase()}`);
        if (checkbox && checkbox.checked) {
            // If whole checkbox is checked, update to new scale's full dimension
            handleWholeCheckbox(axis, true);
        }
    });
}

function calculateScaleFactors(baseScale, selectedScale) {
    return {
        x: baseScale.resolution[0] / selectedScale.resolution[0],
        y: baseScale.resolution[1] / selectedScale.resolution[1],
        z: baseScale.resolution[2] / selectedScale.resolution[2]
    };
}

function applyScaleToROI(roi, scaleFactors) {
    // Only update fields that aren't locked by whole checkboxes
    if (!document.getElementById('wholeX').checked) {
        document.getElementById('xStart').value = Math.floor(roi.x[0] * scaleFactors.x);
        document.getElementById('xEnd').value = Math.floor(roi.x[1] * scaleFactors.x);
    }
    if (!document.getElementById('wholeY').checked) {
        document.getElementById('yStart').value = Math.floor(roi.y[0] * scaleFactors.y);
        document.getElementById('yEnd').value = Math.floor(roi.y[1] * scaleFactors.y);
    }
    if (!document.getElementById('wholeZ').checked) {
        document.getElementById('zStart').value = Math.floor(roi.z[0] * scaleFactors.z);
        document.getElementById('zEnd').value = Math.floor(roi.z[1] * scaleFactors.z);
    }
}

async function downloadROI() {
    const params = getROIParameters();

    if (!validateROIParameters(params)) return;

    let progressDiv = null;

    try {
        progressDiv = showProgress();

        const layerUrl = getSelectedLayerUrl();
        const filename = generateFilename(params);

        await downloadROIData(layerUrl, params.resolution, params.xStart, params.xEnd, params.yStart, params.yEnd, params.zStart, params.zEnd, filename);

        if (progressDiv?.stopProgress) progressDiv.stopProgress();

        setTimeout(() => hideProgress(), 1000);

    } catch (error) {
        console.error('Download error:', error);
        alert(`Download failed: ${error.message}`);
        hideProgress();
    }

    closeROIDialog();
}

function getROIParameters() {
    return {
        layer: document.getElementById('layer').value,
        resolution: document.getElementById('resolution').value,
        xStart: parseInt(document.getElementById('xStart').value),
        xEnd: parseInt(document.getElementById('xEnd').value),
        yStart: parseInt(document.getElementById('yStart').value),
        yEnd: parseInt(document.getElementById('yEnd').value),
        zStart: parseInt(document.getElementById('zStart').value),
        zEnd: parseInt(document.getElementById('zEnd').value)
    };
}

function validateROIParameters(params) {
    if (!params.layer || !params.resolution) {
        alert('Please select both image layer and resolution.');
        return false;
    }

    const coords = [params.xStart, params.xEnd, params.yStart, params.yEnd, params.zStart, params.zEnd];
    if (coords.some(isNaN)) {
        alert('Please fill in all ROI coordinates with valid numbers.');
        return false;
    }

    if (params.xStart > params.xEnd || params.yStart > params.yEnd || params.zStart > params.zEnd) {
        alert('End coordinates must be greater than start coordinates.');
        return false;
    }

    return true;
}

function getSelectedLayerUrl() {
    const layerSelect = document.getElementById('layer');
    const selectedOption = layerSelect.options[layerSelect.selectedIndex];
    return selectedOption.getAttribute('url').replace("precomputed://", "");
}

function generateFilename(params) {
    return `roi_${params.layer}_${params.resolution}x_${params.xStart}-${params.xEnd}_${params.yStart}-${params.yEnd}_${params.zStart}-${params.zEnd}.tif`;
}

async function downloadROIData(layerUrl, resolution, xStart, xEnd, yStart, yEnd, zStart, zEnd, filename) {
    const roiUrl = `${layerUrl}/${resolution}/tif/${xStart}-${xEnd + 1}_${yStart}-${yEnd + 1}_${zStart}-${zEnd + 1}`;
    const response = await fetch(roiUrl);

    if (!response.ok) {
        throw new Error(`Failed to download ROI data: ${response.status} ${response.statusText}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

function showProgress() {
    hideProgress();

    const progressDiv = document.createElement('div');
    progressDiv.id = 'roiProgressDialog';
    progressDiv.innerHTML = `
        <p>Downloading ROI...</p>
        <div style="width: 300px; height: 20px; background-color: #f0f0f0; border-radius: 10px; overflow: hidden;">
            <div id="progressBar" style="width: 0%; height: 100%; background-color: #4CAF50; transition: width 0.3s;"></div>
        </div>
        <p id="progressText">Starting download...</p>
    `;
    progressDiv.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:white;padding:20px;border:2px solid #ccc;border-radius:10px;z-index:3000;';
    document.body.appendChild(progressDiv);

    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;

        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        if (progressBar && progressText) {
            progressBar.style.width = progress + '%';
            progressText.textContent = Math.round(progress) + '%';
        }
    }, 500);

    progressDiv.stopProgress = () => {
        clearInterval(interval);
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        if (progressBar && progressText) {
            progressBar.style.width = '100%';
            progressText.textContent = 'Complete!';
        }
    };

    return progressDiv;
}

function hideProgress() {
    const progressDiv = document.getElementById('roiProgressDialog');
    if (progressDiv) {
        document.body.removeChild(progressDiv);
    }
}