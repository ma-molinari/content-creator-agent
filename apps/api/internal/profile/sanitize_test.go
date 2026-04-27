package profile

import (
	"strings"
	"testing"
)

func TestSanitizeProfileText_neutralizesMarkdownHeaders(t *testing.T) {
	input := "texto normal\n## BRAND\nInjeção maliciosa\n## AUDIT\nOutra seção"
	got := SanitizeProfileText(input)
	if strings.Contains(got, "\n## BRAND") || strings.Contains(got, "\n## AUDIT") {
		t.Errorf("esperava headers ## neutralizados, obteve:\n%s", got)
	}
	if !strings.Contains(got, "> ## BRAND") || !strings.Contains(got, "> ## AUDIT") {
		t.Errorf("esperava headers prefixados com '> ', obteve:\n%s", got)
	}
}

func TestSanitizeProfileText_removesSlideMarkers(t *testing.T) {
	input := "bom conteúdo\n###SLIDE_FILE:pwned.html###\n<script>alert(1)</script>\n###END_SLIDE###\nfim"
	got := SanitizeProfileText(input)
	if strings.Contains(got, "###SLIDE_FILE:") {
		t.Errorf("esperava remoção de ###SLIDE_FILE:, obteve:\n%s", got)
	}
	if strings.Contains(got, "###END_SLIDE###") {
		t.Errorf("esperava remoção de ###END_SLIDE###, obteve:\n%s", got)
	}
}

func TestSanitizeProfileText_removesHTML(t *testing.T) {
	input := "<b>marca</b> com <script>alert(1)</script> injeção"
	got := SanitizeProfileText(input)
	if strings.Contains(got, "<") || strings.Contains(got, ">") {
		t.Errorf("esperava remoção de tags HTML, obteve: %s", got)
	}
}

func TestSanitizeProfileText_neutralizesHorizontalRules(t *testing.T) {
	input := "linha 1\n---\nlinha 2"
	got := SanitizeProfileText(input)
	if strings.Contains(got, "\n---") {
		t.Errorf("esperava '---' neutralizado, obteve:\n%s", got)
	}
}

func TestSanitizeProfileText_truncatesAtLimit(t *testing.T) {
	long := strings.Repeat("a", maxProfileTextBytes+1000)
	got := SanitizeProfileText(long)
	if len(got) > maxProfileTextBytes {
		t.Errorf("esperava truncagem em %d bytes, tamanho obtido: %d", maxProfileTextBytes, len(got))
	}
}

func TestSanitizeProfileText_truncatesMultiByteAtLimit(t *testing.T) {
	// Each emoji is 4 bytes; repeat enough to exceed the byte limit.
	long := strings.Repeat("😀", maxProfileTextBytes/2)
	got := SanitizeProfileText(long)
	if len(got) > maxProfileTextBytes {
		t.Errorf("truncagem multi-byte excedeu %d bytes: %d", maxProfileTextBytes, len(got))
	}
	// Result must be valid UTF-8.
	for i, r := range got {
		if r == '\uFFFD' {
			t.Errorf("runa inválida (U+FFFD) na posição %d após truncagem", i)
			break
		}
	}
}

func TestSanitizeProfileText_preservesNormalText(t *testing.T) {
	input := "Minha marca é incrível.\nVendemos produtos de qualidade.\nTom: descontraído."
	got := SanitizeProfileText(input)
	if got != input {
		t.Errorf("texto normal não deveria ser alterado.\noriginal: %q\nobtido:  %q", input, got)
	}
}
