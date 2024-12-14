# ASCII Art Compression for IQ6900

Compression is typically divided into two types:
- **Type where deduplication works**
- **Type where deduplication is ineffective**

## Version without Deduplication

This method guarantees a **59.83%** compression rate for all images.

1. **Map ASCII art to numbers from 0 to 6**.
2. **Convert from base 7 to base 10**.
3. **Convert from base 10 to base 127**.

### Decoding Method

- **Convert from base 127 to base 10**.
- **Convert from base 10 to base 7**.
- **Map number to ASCII art**.

## Version with Deduplication

Since we aim to always use the more efficient compression, using this method means the compression rate would be **59.83% + α**.

### Custom RLE Compression Algorithm

We've modified RLE compression to create our custom compression algorithm.

1. **Perform RLE-based compression**.
   - Example: Characters with their repetition counts, like `a1b2c3`.

2. **Separate characters and numbers**, and map the characters to **0-6**.
   - Example: `a1b2c3` -> Number array `[1, 2, 3]` and character array `[0, 1, 2]` (where 'a' maps to 0, 'b' to 1, 'c' to 2).

3. **Append the character array to the number array**.

#### Note

- Formats like `a12b2` would be **useless** because numbers should not exceed one digit. Thus, numbers are **limited to 9**.

4. **Convert the decimal number array to base 127**.

### Decoding Method

- **Convert from base 127 to base 10**.
- **Split the array into halves**, then map the characters back using **ASCII mapping**.
- **Perform RLE decoding**.

### Conclusion

With this method, we support **over 59.83% lossless compression** for ASCII art.
