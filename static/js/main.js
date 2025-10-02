// Инициализируем API Telegram Mini App
const tg = window.Telegram.WebApp;
tg.ready(); // Сообщаем Telegram, что приложение готово к отображению

// --- Глобальные переменные и элементы DOM ---
const startBtn = document.getElementById('start_btn');
const pingOutput = document.getElementById('ping_output');
const downloadOutput = document.getElementById('download_output');
const uploadOutput = document.getElementById('upload_output');
const progressBar = document.getElementById('progress_bar');
const logOutput = document.getElementById('log_output');
const clientInfoOutput = document.getElementById('client_info_output');
const serverInfoOutput = document.getElementById('server_info_output');
const networkInfoOutput = document.getElementById('network_info_output');
const timeoutSlider = document.getElementById('timeout_slider');
const sliderValue = document.getElementById('slider_value');

let testInProgress = false;
let fullLog = "";
let clientGeoInfo = {};

// --- Функции для логов и интерфейса ---
function log(message) {
    const timestamp = new Date().toLocaleTimeString();
    const logMessage = `[${timestamp}] ${message}\n`;
    fullLog += logMessage;
    logOutput.textContent += logMessage;
    logOutput.scrollTop = logOutput.scrollHeight; // Автопрокрутка вниз
}

function updateProgressBar(percentage) {
    progressBar.style.width = `${percentage}%`;
}

function formatSpeed(speedMbps) {
    return `${speedMbps.toFixed(2)} <small>Мбит/с</small>`;
}

// --- Логика тестов ---

// 1. Тест пинга
async function testPing() {
    log("Начинаю тест пинга...");
    const startTime = Date.now();
    try {
        // Добавляем случайный параметр, чтобы избежать кэширования
        await fetch('/ping?t=' + startTime, { cache: 'no-store' });
        const endTime = Date.now();
        const pingTime = endTime - startTime;
        log(`Пинг успешный: ${pingTime} мс`);
        pingOutput.innerHTML = `${pingTime} <small>мс</small>`;
        return pingTime;
    } catch (error) {
        log("Ошибка в тесте пинга: " + error);
        pingOutput.textContent = "Ошибка";
        return -1;
    }
}

// 2. Тест загрузки (Download)
async function testDownload() {
    log("Начинаю тест загрузки...");
    const testDuration = parseInt(timeoutSlider.value, 10) * 1000;
    let totalBytes = 0;
    const startTime = Date.now();

    const controller = new AbortController();
    const signal = controller.signal;
    const timeout = setTimeout(() => controller.abort(), testDuration);

    try {
        const response = await fetch('/download?size=16777216', { signal, cache: 'no-store' });
        const reader = response.body.getReader();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            totalBytes += value.length;
            const elapsedTime = Date.now() - startTime;
            const speedMbps = (totalBytes * 8) / (elapsedTime / 1000) / 1000000;
            downloadOutput.innerHTML = formatSpeed(speedMbps);
            updateProgressBar((elapsedTime / testDuration) * 100);
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            log("Тест загрузки завершен по времени.");
        } else {
            log("Ошибка в тесте загрузки: " + error);
            downloadOutput.textContent = "Ошибка";
        }
    } finally {
        clearTimeout(timeout);
    }

    const finalElapsedTime = Date.now() - startTime;
    const finalSpeedMbps = (totalBytes * 8) / (finalElapsedTime / 1000) / 1000000;
    log(`Итоговая скорость загрузки: ${finalSpeedMbps.toFixed(2)} Мбит/с`);
    downloadOutput.innerHTML = formatSpeed(finalSpeedMbps);
    return finalSpeedMbps;
}

// 3. Тест отправки (Upload)
async function testUpload() {
    log("Начинаю тест отправки...");
    const testDuration = parseInt(timeoutSlider.value, 10) * 1000;
    let totalBytes = 0;
    const chunkSize = 256 * 1024; // 256 KB
    const data = new Uint8Array(chunkSize); // Создаем "пустые" данные для отправки
    const startTime = Date.now();

    async function uploadChunk() {
        if (Date.now() - startTime > testDuration) return;

        try {
            await fetch('/upload', { method: 'POST', body: data, cache: 'no-store' });
            totalBytes += chunkSize;
            const elapsedTime = Date.now() - startTime;
            const speedMbps = (totalBytes * 8) / (elapsedTime / 1000) / 1000000;
            uploadOutput.innerHTML = formatSpeed(speedMbps);
            updateProgressBar((elapsedTime / testDuration) * 100);
            await uploadChunk(); // Рекурсивно вызываем следующую отправку
        } catch (error) {
            log("Ошибка в тесте отправки: " + error);
            uploadOutput.textContent = "Ошибка";
        }
    }
    
    await uploadChunk();

    const finalElapsedTime = Date.now() - startTime;
    const finalSpeedMbps = (totalBytes * 8) / (finalElapsedTime / 1000) / 1000000;
    log(`Итоговая скорость отправки: ${finalSpeedMbps.toFixed(2)} Мбит/с`);
    uploadOutput.innerHTML = formatSpeed(finalSpeedMbps);
    return finalSpeedMbps;
}

// 4. Отправка результатов боту
function sendResultsToBot(results) {
    log("Отправляю результаты в Telegram...");
    try {
        // Метод sendData отправляет данные (в виде строки) боту
        tg.sendData(JSON.stringify(results));
        log("Результаты успешно отправлены. Можете закрыть это окно.");
        // Опционально: можно автоматически закрыть Mini App
        // tg.close();
    } catch (error) {
        log("Не удалось отправить данные боту: " + error);
    }
}

// --- Главная функция запуска ---
async function runTest() {
    if (testInProgress) return;
    testInProgress = true;
    startBtn.disabled = true;
    fullLog = "";
    logOutput.textContent = "";

    // Сброс интерфейса
    pingOutput.textContent = "-";
    downloadOutput.textContent = "-";
    uploadOutput.textContent = "-";
    updateProgressBar(0);

    log("Начинаю комплексный тест скорости...");

    const pingResult = await testPing();
    updateProgressBar(0);

    const downloadResult = await testDownload();
    updateProgressBar(0);

    const uploadResult = await testUpload();
    updateProgressBar(100);

    log("Тест скорости завершен.");

    const finalResults = {
        ping: `${pingResult.toFixed(0)} мс`,
        download: `${downloadResult.toFixed(2)} Мбит/с`,
        upload: `${uploadResult.toFixed(2)} Мбит/с`,
        clientInfo: clientGeoInfo,
        fullLog: fullLog
    };

    // Отправляем результаты боту
    sendResultsToBot(finalResults);

    testInProgress = false;
    startBtn.disabled = false;
}

// --- Функции инициализации ---
async function getGeoInfo() {
    try {
        const response = await fetch('/get_geo_info');
        const data = await response.json();
        clientGeoInfo = data.user;
        clientInfoOutput.textContent = `${data.user.ip} (${data.user.city}, ${data.user.country})`;
        serverInfoOutput.textContent = `${data.server.ip} (${data.server.city}, ${data.server.country})`;
    } catch (error) {
        clientInfoOutput.textContent = "Не удалось получить";
        serverInfoOutput.textContent = "Не удалось получить";
        log("Ошибка при получении гео-информации.");
    }
}

function getNetworkInfo() {
    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (connection) {
        const type = connection.effectiveType;
        networkInfoOutput.textContent = type.charAt(0).toUpperCase() + type.slice(1);
    } else {
        networkInfoOutput.textContent = "Недоступно";
    }
}

// --- Обработчики событий ---
startBtn.addEventListener('click', runTest);
timeoutSlider.addEventListener('input', () => {
    sliderValue.textContent = timeoutSlider.value;
});

// --- Инициализация при загрузке страницы ---
window.addEventListener('load', () => {
    getGeoInfo();
    getNetworkInfo();
    log("Приложение готово. Нажмите 'Старт' для начала.");
});
