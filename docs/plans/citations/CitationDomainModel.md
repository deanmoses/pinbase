# Citation Domain Model

Pinbase should distinguish between three different things:

1. **Citation source**
   The work or evidence object being cited: a book, manual, web page, video, image, observation record, museum document, interview, etc.

2. **Citation instance**
   A specific use of that source for a specific Pinbase claim or text position, including any locator such as page number, timestamp, or URL fragment.

3. **Access link**
   A way for the reader to inspect the source: canonical URL, archive URL, museum-hosted scan, repository page, uploaded asset, and so on.

These should not be collapsed into one record.

If Pinbase does collapse them, it will have trouble representing cases like:

- the same book cited on different pages
- the same manual available from both a poor internet scan and a later museum-grade scan
- the same video cited at two different timestamps
- a dead URL later replaced by an archived copy
