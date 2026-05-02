import '@testing-library/jest-dom/vitest'

// jsdom lacks Blob URLs; SlideBlobImage and similar need these for RTL tests.
if (typeof URL.createObjectURL !== 'function') {
  let nextBlobId = 0
  URL.createObjectURL = function createObjectURLMock() {
    return `blob:http://localhost/mock-blob-${nextBlobId++}`
  }
}

if (typeof URL.revokeObjectURL !== 'function') {
  URL.revokeObjectURL = function revokeObjectURLMock() {
    /* no-op under jsdom */
  }
}
