/**
 * `PUT` a file to a presigned URL. `fetch` cannot report upload progress, so
 * this is the one place the app uses XMLHttpRequest.
 *
 * The `Content-Type` must be the one the URL was signed for; storage refuses
 * anything else.
 */
export function putFile(
  url: string,
  file: File,
  contentType: string,
  onProgress?: (fraction: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", contentType);
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && onProgress) onProgress(event.loaded / event.total);
    });
    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Storage refused the upload (${xhr.status})`));
    });
    xhr.addEventListener("error", () => reject(new Error("The upload could not reach storage.")));
    xhr.addEventListener("abort", () => reject(new Error("The upload was cancelled.")));
    xhr.send(file);
  });
}

/** What the browser reports, or the generic type when it reports nothing. */
export function contentTypeOf(file: File): string {
  return file.type || "application/octet-stream";
}
