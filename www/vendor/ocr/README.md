# Offline OCR (vendored)

- `tesseract.min.js`, `worker.min.js`: tesseract.js 5.1.1 (Apache-2.0)
- `tesseract-core-lstm.wasm.js`: tesseract-core 5.1.1 LSTM engine with WebAssembly embedded (Apache-2.0)
- `eng.traineddata.gz`: English data, "best int" 4.0.0 from @tesseract.js-data/eng 1.0.0 (Apache-2.0, from tessdata_best)

Loaded only when the Import PDF resume tool reads a scan or a photo.
