# Stephanie Falanque — sistema de marca (posts e carrosséis)

**Handle:** `@stephaniefalanque`  
**Função pública (lockup):** Psicóloga de Jovens Adultas  
**Nicho:** jovens adultas — autonomia, limites, maturidade emocional, ansiedade e padrões relacionais  
**Idioma:** português brasileiro (PT-BR)  
**CRP:** 06/188033  
**Link de conversão:** `bio.site/stephaniefalanque` (agendamentos)  
**Abordagens citadas na bio:** TCC, DBT · sessões online  

**Documentos irmãos:** `AUDIT.md` (evidências, limitações da captura, recomendações estratégicas). Este ficheiro concentra **regras reutilizáveis** para copy e slides; validação visual de carrossel continua a cruzar com `AUDIT.md` e previews.

---

## 1. Estratégia e posicionamento

### Propósito (síntese)

Ajudar jovens adultas a reconstruir com consciência o que foi moldado pela dor, retomando autonomia, limites e identidade própria — sem depender da validação externa.

### Público

- Mulheres jovens adultas em transição (relações, trabalho, família de origem).
- Quem vive automático, “versão editada” de si, medo de abandono, interpretação personalizada excessiva (tudo “é sobre mim”).
- Tom de **parceria** (“juntas”, “a gente olha pra isso”), sem infantilizar.

### Pilares de conteúdo (derivados do feed auditado)

1. **Autonomia e limites** — sair de onde não há vontade, não se abandonar para manter vínculos.
2. **Padrões e narrativa** — caos como origem de mudança; consciência sobre moldes antigos.
3. **Regulação e TCC/DBT (implícito)** — tolerar o que se sente, reduzir tribunal interno, fatos vs. suposições.
4. **Relacionamentos e autoimagem** — migalhas, medo de abandono, comparação, ser “menos intensa”.
5. **Micro-ações** — convites a testar comportamentos na semana (comentário numerado, guardar).

### Promessa e credenciais

- Bio: linha única sobre autonomia e limites + online + TCC/DBT + CRP + CTA agendamentos.
- Nos slides: manter **credibilidade clínica** sem visual “hospital frio”; linguagem **acessível e contemporânea**.

### Mix editorial (referência)

- Feed com forte peso em **carrosséis** (~78% na amostra `04_posts`), retratos com headline, colagens, texturas, acentos rosa.
- **Reels** na grelha quebram padrão estático — manter miniatura reconhecível (rosto / marca / cor).

---

## 2. Identidade visual (carrossel e gráficos)

### Paleta (tokens CSS — pasta `carousels/.../slides.css`)

| Token / uso | Hex | Notas |
|-------------|-----|--------|
| Magenta (acento principal) | `#e02d8c` | Faixas, bullets, destaques |
| Magenta profundo | `#c41e7a` | Variação |
| Rosa poeira | `#c97b95` | Faixas secundárias, callouts |
| Rosa poeira claro | `#dfa8b8` | Detalhes, cutouts |
| Papel / off-white | `#ebe8e6`, `#f2efec` | Fundos tipo papel |
| Preto suave | `#1a1a1a` | Texto forte |
| Grafite / corpo | `#2e2e2e`, `#333333` | Texto, blocos escuros |
| Cinzas | `#5c5654`, `#6e6865` | Numeração, secundário |
| Branco | `#ffffff` | Texto sobre magenta e blocos escuros |
| Mauve / fundo sólido | `#b87498` | Fundo integral nos slides T4 (dusty rose médio) |

**Na grelha (fotografia):** rosa/magenta como acento, preto, branco/off-white, cinzas texturados, amarelo pontual (stickers/destaques). Modo escuro do app realça contraste da bio.

### Tipografia

| Família | Uso | Pesos / estilo |
|---------|-----|----------------|
| **Montserrat** | Sans-serif primária — faixas magenta, lockup, corpo editorial, templates T1/T4/T5 | 400, 600, 700, 800, 900; itálico pontual |
| **Serif display** (Playfair Display ou Cormorant) | Storytelling atmosférico — templates T2 e T6 serif; slides sem foto de fundo; títulos de colagem (T3) | Regular, Italic, Bold — texto branco sobre fundo escuro ou preto sobre off-white |
| **Script / escrita manual** (Caveat ou Dancing Script) | Acentos pontuais — taglines curtas ("comigo!"), texto "Na prática:" nas pastas manila (T3B), handle script em T4 | Regular; nunca em títulos principais |

- Hierarquia: títulos em **uppercase** pesado nas faixas magenta; corpo 22–26px, legível em mobile 9:16.
- Em T4 (mauve sólido) o bold do título parece mais condensado/compacto que Montserrat padrão — pode ser Montserrat Black com `letter-spacing` negativo ou variante condensed.

### Lockup obrigatório (barra de marca) e variantes

**Variante A — Barra topo completa** (templates T1, T5; posts p004, p005, p007)
- Linha única horizontal no topo: `@STEPHANIEFALANQUE` `//` `PSICÓLOGA DE` / `JOVENS ADULTAS` (duas linhas à direita).
- Estilo: uppercase, letter-spacing ~0.12em, peso 700, pequeno (~10px) — ver classes `.brand-bar` em `slides.css`.
- Sobre fotos escuras: variante clara (`.brand-bar--light`); sobre papel: escura (`.brand-bar--dark`).

**Variante B — Handle rodapé** (templates T2, T3, T3B; posts p001 inner, p002, p003, p006)
- `@stephaniefalanque` isolado, lowercase, canto inferior centro.
- Sem "Psicóloga de Jovens Adultas". Peso normal ou leve, tamanho pequeno.
- Usada quando o slide tem foto de fundo integral ou fundo escuro e o lockup barra topo comprometeria a leitura.

**Variante C — Handle canto topo script** (template T4; p008)
- `@stephaniefalanque` canto superior esquerdo em fonte script/itálico fino (não uppercase).
- Sem "Psicóloga de Jovens Adultas" e sem separador `//`.
- Específica para o template mauve sólido onde o bold do título já ancora a marca.

**Variante D — Handle entre filetes** (template T6 sans; p009)
- `@stephaniefalanque` centralizado horizontalmente, flanqueado por dois filetes finos (`1px`) acima e abaixo no topo do slide.
- Fonte regular, lowercase, tracking normal — serve como "cabeçalho de página editorial".
- Exclusive do template T6 variante sans.

### Motivos e estilo gráfico

- Colagem, papel texturado, silhuetas, estrelas, polaroid — **terapia acessível**, não clínica gelada.
- Faixas magenta com leve rotação (`strip--tilt`) e sombra suave são assinatura.
- Humor/meme **pontual**; se for regra, dilui autoridade — usar como exceção.

### Numeração de slides e slide CTA final

**Badge de numeração** (template T6 — p009)
- Círculo sólido rosa (~`#e02d8c`), diâmetro ~32px, canto inferior direito.
- Texto branco centrado no badge: `NN/TT` (ex: `01/08`).
- Posicionado acima da linha de rodapé/filete inferior do template.
- Não usar em templates com faixa magenta de título (T1) ou em slides de foto integral.

**Slide CTA final** (padrão reutilizável em qualquer template — p009 slide 05)
- Três ícones rosa (`#e02d8c` ou `#c97b95`) dispostos horizontalmente em linha:
  - Coração (curtir) · Marcador/bookmark (salvar) · Avião-papel (compartilhar)
- Abaixo de cada ícone: label uppercase curto e centralizado, ex: `CURTE O POST` · `SALVA PRA VER DEPOIS` · `COMPARTILHA COM QUEM PRECISA`
- Fundo: herda o fundo do template (off-white em T6, mauve em T4, etc.)
- Separado do corpo do carrossel por espaço vertical generoso — slide dedicado exclusivo.
- Pode substituir ou complementar o CTA textual da legenda.

---

### Layout 9:16 (768×1376)

- **Área útil do miolo:** abaixo do lockup (~86px+), acima da zona segura inferior **~276–300px** (UI do Instagram + numeração tipo `01 / 06`).
- Conteúdo esparso: **centrar verticalmente** o miolo nessa faixa (ver skill create-social-posts).

### Templates visuais (T1–T6)

Os posts reais de `04_posts` revelam seis templates distintos. Ao criar um post novo, escolher o template antes de produzir copy ou slides.

| Template | Posts de referência | Fundo | Tipografia principal | Lockup |
|----------|--------------------|----|---|---|
| T1 — Editorial Photo + Faixa | p001 capa, p004, p007 | Foto lifestyle integral | Montserrat ExtraBold uppercase branco | Barra topo completa |
| T2 — Storytelling Escuro | p002 | Grafite/preto bokeh | Serif display fino branco + itálico rosa | Apenas handle rodapé |
| T3 — Colagem Papel | p003 slide 01, 05 | Papel texturado cinza | Serif bold display + script tagline | Handle rodapé |
| T3B — Colagem Escura + Pasta | p003 slides 2–4 | Grafite/preto | Sans-serif bold branco + script rosa (pasta) | Handle rodapé |
| T4 — Mauve Sólido | p008 | Mauve `#b87498` integral | Sans-serif bold condensado grafite | Handle script canto topo esq. |
| T5 — Info Carousel Light | p005 slides 2, 4 | Off-white `#f2efec` | Montserrat corpo + callout rosa | Barra topo completa |
| T6 — Tipografia Off-White | p006, p009 | Creme `#ebe8e6` | Serif display (p006) ou sans-serif bold (p009) | Filete + handle topo (p009) |

**Regras por template:**

**T1 — Editorial Photo + Faixa Magenta**
- Foto lifestyle ou editorial como fundo integral (mulheres, rua, cotidiano, meme animal com personalidade).
- Faixa magenta `#e02d8c` posicionada no primeiro terço — texto uppercase Montserrat ExtraBold branco.
- Caixa secundária rosa-poeira (`#c97b95`) para subtítulo ou corpo curto, sem fundo opaco total.
- Acentos gráficos esparsos: ✨ ✦ ou stickers de estrela.
- Lockup barra topo completo obrigatório.

**T2 — Storytelling Escuro**
- Fundo grafite escuro bokeh — pode ser foto de Stephanie desfocada ou interior escuro.
- Capa (slide 01): foto de Stephanie em ângulo elegante + overlay tipográfico misto (bold sans + caixa rosa no word-destaque).
- Slides interiores: apenas texto; serif display regular/italic branco; destaques em itálico rosa-poeira (`#dfa8b8`–`#c97b95`); texto alinhado à esquerda.
- Sem lockup barra; sem fotos nos slides interiores.
- Indicado para: storytelling pessoal, origem, propósito, narrativa de transformação.

**T3 — Colagem / Textura de Papel**
- Fundo papel texturado acinzentado (grain/noise).
- Título principal: serif bold display black grande, sentence case ou lowercase.
- Tagline logo abaixo em script/cursiva itálica.
- Cutout B&W de Stephanie centralizado ou à direita.
- Formas gráficas magenta ou rosa (estrela burst, raios) por trás do cutout — símbolo de energia/destaque.
- Handle `@stephaniefalanque` rodapé, peso normal pequeno.

**T3B — Colagem Escura com Pasta Manila**
- Fundo grafite/preto.
- Título: sans-serif bold ExtraBold branco, grande, em sentence case declarativa curta (ex: "Eu separo culpa de responsabilidade.").
- Subtítulo: sans-serif regular cinza claro, corpo de apoio.
- Prop pasta manila: imagem de pasta de arquivo com aba lilás, posicionada no centro-inferior; texto "Na prática:" em serif pequeno + corpo em script rosa-magenta simulando caneta.
- Handle `@stephaniefalanque` rodapé, peso normal.

**T4 — Monochrome Mauve Sólido**
- Fundo integral mauve `#b87498` — sem fotos, sem faixas.
- Título uppercase bold condensado, cor grafite escuro `#2e2e2e` (não branco).
- Subtítulo: mesma família cromática mas mais claro (rosa-blush ~`#dfa8b8`), weight regular, centered.
- Handle `@stephaniefalanque` canto superior esquerdo em script fino ou itálico (não uppercase, não barra completa).
- Indicado para: frases de validação emocional, contagem de itens, punches curtos serializados.

**T5 — Info Carousel Light**
- Fundo off-white/cinza muito claro `#f2efec`.
- Lockup barra topo completo obrigatório.
- Texto corpo sans-serif, justificado, tamanho legível (~22–26px).
- Callout box: fundo rosa-poeira médio (`#c97b95`) com texto bold branco — para o insight principal do slide.
- Imagens de produto/lifestyle (sem fundo ou com fundo cortado) ao lado do texto como apoio visual.
- Indicado para: educação com exemplos concretos, listas com contexto, análise comportamental.

**T6 — Tipografia Minimalista Off-White**
- Fundo creme off-white `#ebe8e6` a `#f2efec`.
- Variante serif (p006): título grande em serif display, preto, sentence case; uma palavra-chave em rosa itálico (`#c97b95`); sem lockup; handle rodapé centro pequeno.
- Variante sans (p009): título grande Montserrat bold, sentence case, preto; lockup T6 próprio (handle entre dois filetes horizontais finos no topo); slide body com texto centrado regular; slide final CTA com 3 ícones.
- Badge de numeração no canto inferior direito (ver seção abaixo).
- Indicado para: desconstrução de mitos, listas de redefinição, conteúdo reflexivo minimalista.

---

### Grade (quando houver `03_grid/*.png`)

- Topo com posts fixados de onboarding (terapia, motivos, história).
- Ritmo: alternância retrato + headline / lifestyle / flat lay / colagem; blocos rosa para scan rápido.
- Risco: muitos carrosséis seguidos homogeneizam miniatura — variar capa (cor, tipografia, foto).

---

## 3. Voz, tom e legenda

### Características

1. **Segunda pessoa** (“você”, “sua”) e **inclusão situacional** (“se isso bateu aí”, “juntas”).
2. **Acolhimento + honestidade** — valida sofrimento e nomeia padrão sem julgar.
3. **Educação leve** — listas, bullets mentais, “tem nome:”.
4. **Provocação gentil** — perguntas de reflexão no fecho (autonomia, história).
5. **Ritmo variado** — legendas muito curtas (convite, punch) e longas (storytelling tipo `p002`).

### O que evitar

- **Linhas “SEO:”** no texto publicado — são notas de planeamento; não ir para o Instagram.
- **Hashtags desalinhadas** — rever antes de publicar (ex.: `#compras` em post clínico foi apontado como lapso no audit).
- Promessas de cura, diagnóstico pela internet ou substituição de terapia presencial quando não aplicável.

### Hashtags (padrão observado)

- Conjuntos curtos (3–4): `#psicologia` `#terapia` `#jovemadulta` `#autonomia` `#maturidade` etc.
- Campanhas pontuais: `#desafiowonderup` (exemplo na amostra).

### CTAs — escolher conforme objetivo

| Objetivo | Exemplos alinhados ao feed |
|----------|----------------------------|
| Comentário | “Comenta 1, 2 ou 3”, “Qual card parece com a sua vida?” |
| Guardar | “Salva pra usar depois”, “Salva pra lembrar quando a culpa aparecer” |
| Partilha implícita | “Alguém que você conhece também precisa ler isso” |
| Conversão | “Clica no link da bio”, “Me chama no direct” |
| Só reflexão | Pergunta final sem link — ok; considerar **uma linha** opcional de bio em posts longos só educativos |

### Emojis

- Uso **moderado** para scan (💐 💖 ✨ 👀 🗣️ 📌 💬 ✍🏻); não poluir títulos clínicos.

---

## 4. Checklist rápido (antes de publicar)

**Copy**

- [ ] PT-BR, tom “jovens adultas”, segunda pessoa.
- [ ] CTA coerente com o objetivo do post.
- [ ] Hashtags revisadas; sem lixo de planeamento no texto.
- [ ] Sem promessa irresponsável; CRP/bio já cobrem credencial (não repetir CRP em todo post salvo contexto legal/ético).

**Carrossel (HTML/CSS)**

- [ ] Template escolhido (T1–T6) declarado antes de iniciar — ver seção “Templates visuais” acima.
- [ ] Lockup na variante correta para o template (A, B, C ou D — ver seção Lockup).
- [ ] Paleta e tipografia alinhadas ao template escolhido e a `slides.css` existente ou tokens deste documento.
- [ ] Zona segura inferior respeitada; miolo centrado se o slide for “magro”.
- [ ] Pré-validação Playwright + `validation-report.md` vs. `AUDIT.md`.

---

## 5. Referência de ficheiros no repositório

| Conteúdo | Local |
|----------|--------|
| Bio | `01_profile/bio.txt` |
| Legendas amostra | `04_posts/p001_caption.txt` … `p009_caption.txt` |
| Grelha (se existir) | `03_grid/*.png` |
| Tokens e componentes de slide | `carousels/<slug>/slides.css` |
| Auditoria e evidências | `AUDIT.md` |

---

*Sistema derivado do Instagram Curator + análise das legendas `04_posts`, bio, `AUDIT.md` e implementação em `carousels/`. Atualizar este ficheiro se a bio, paleta ou lockup mudarem.*
