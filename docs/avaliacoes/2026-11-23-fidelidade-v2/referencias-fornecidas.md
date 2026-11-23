# Validação com referências fornecidas — 23/11/2026

## Método

Com autorização do usuário, duas imagens de referência foram enviadas ao S3 e à
OpenAI para um ensaio isolado em Docker. Foram produzidos quatro carrosséis de
três slides, com o mesmo pedido e perfil de teste: controle sem referência, uma
geração com cada imagem separadamente e outra com ambas. A API, o worker, o
PostgreSQL e o Chromium foram executados na stack de teste; o S3 e o modelo foram
reais. A geração é não determinística e há apenas uma amostra por condição.

Os arquivos originais, snapshots completos, slides e comparativo com as imagens do
usuário ficaram somente em `.local/`, fora do repositório. Os chats e referências
temporários foram excluídos após os jobs terminarem; a listagem dos prefixos das
quatro contas e dos quatro jobs encontrou zero objetos restantes no S3. A direção temporária extraída
pelo modelo não foi persistida, logo o relatório não comprova como cada detalhe
foi classificado durante a análise.

## Resultado

| Condição | Imagens de referência inseridas nos slides | Contraste mínimo de texto do snapshot |
| --- | ---: | ---: |
| Sem referência | 0 | 4,77:1 |
| Referência 1 | 1 | 15,91:1 |
| Referência 2 | 0 | 4,81:1 |
| Ambas | 2 | 17,07:1 |

As referências influenciaram as cores de destaque: o controle usou tons quentes
amarronzados; as outras condições escolheram tons rosados ou arroxeados. Esse
resultado não comprova consistência estatística. As composições permaneceram
majoritariamente em fundo sólido com texto e barras ou linhas, sem reconstruir
os recortes, texturas, ilustrações, tipografia e fotografia presentes nas
referências. Nos cenários que inseriram imagens, o resultado incorporou capturas
inteiras com seu conteúdo original, não uma reconstrução editável do estilo.

O contraste acima foi calculado a partir das cores resolvidas dos elementos de
texto do snapshot contra o fundo sólido; não inclui texto contido nas imagens
incorporadas nem substitui inspeção de pixels ou auditoria de acessibilidade.
Todas as saídas tiveram 1080 × 1350 pixels e foram inspecionadas visualmente.

## Operação e pendências

Os quatro jobs concluíram; os logs agregados registraram duas falhas de validação
intermediárias que foram recuperadas por retentativa. O p95 de duração dos jobs foi
32.092 ms para esta amostra pequena, sem meta definida. Custos e tokens não foram
medidos. Falta validar o coletor e o rollout/rollback no ambiente de destino.

O responsável não aprovou a fidelidade visual e decidiu que referências servem
apenas como orientação, salvo pedido explícito de inclusão. A geração atual ainda
permite incorporá-las automaticamente; a correção dessa divergência está pendente.
A V2 não deve ser ativada em tráfego
antes do aceite visual e operacional, da definição de metas e da conclusão da T18
híbrida. O sucesso dos jobs não demonstra reprodução fiel das referências.
