/**
 * Password transport for `/auth/login`, `/auth/register`, and `/auth/recover-password`.
 * V1: API expects plaintext JSON over HTTPS (bcrypt on server). Replace with RSA
 * if the API exposes a public key and accepts ciphertext.
 */
export function preparePasswordForTransport(plain: string): string {
  return plain
}
