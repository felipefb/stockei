/**
 * Stockei — testes das constantes/contratos do streaming de câmera.
 * Rodar: node frontend/camera_tests.js
 */

const assert = require("assert");
const { TARGET_SIZE, JPEG_QUALITY, STREAM_FPS } = require("./camera_streaming.js");

// Contratos definidos no PROMPT 2.1
assert.strictEqual(TARGET_SIZE, 640, "Frames devem ser 640x640");
assert.strictEqual(JPEG_QUALITY, 0.8, "Compressão JPEG deve ser 80%");
assert.ok(STREAM_FPS >= 3 && STREAM_FPS <= 5, "Streaming deve ser 3-5 FPS");

console.log("camera_tests.js: 3 asserts OK");
