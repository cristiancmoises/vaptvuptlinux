<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Cristian Cezar Moisés. -->
# Escopo, proveniência e bloqueio do kernel

[English](development.md)

A entrega 0.1.0-dev.1 consiste em ferramentas em espaço de usuário. As
ferramentas próprias usam Apache-2.0 sob autorização do titular dos direitos
autorais. Essa autorização não licencia uma implementação para o kernel.
Nenhum arquivo de implementação do codec ou do kernel foi importado ou
relicenciado neste pacote.

O snapshot local herdado, sem Git, declara Linux 7.2.7 no Makefile e contém
uma amalgamação VaptVupt 2.65.11 marcada GPL-3.0-or-later. Seu commit upstream
exato é desconhecido. Os hashes em PROVENANCE.json identificam quatro
arquivos locais observados, não uma árvore completa, versão upstream nem
build verificado. O wrapper histórico não é o backend deste pacote.

O codec canônico externo 2.65.13 atualmente declara Apache-2.0 para o código
próprio e BSD-2-Clause para sua implementação XXH64 derivada do xxHash.
O inventário de fontes compilado pelo Makefile consiste em sete arquivos C
e todos os headers públicos de include. O verificador rejeita declarações
de licença ausentes/múltiplas, licenças ou versão do codec inesperadas,
avisos ausentes, arquivos/diretórios de dependência que sejam links
simbólicos e arquivos acima de 2 MiB. Informa um digest do inventário
ordenado de fontes/headers. Esta verificação limitada não é uma auditoria
completa de direitos autorais, atestado de autenticidade nem concessão de
implementação compatível. Não examina projetos alheios nem o kernel completo.

As [regras de licenciamento do kernel](https://docs.kernel.org/process/license-rules.html)
especificam somente a versão 2 da GPL para o kernel como um todo e exigem
licenças de arquivos compatíveis. Apache-2.0 está listada para licenciamento
duplo, com uma alternativa compatível. Por isso, este pacote mantém um
bloqueio obrigatório: não há concessão compatível revisada nem backend.
Alterar a string de licença de um módulo não mudaria os direitos da
implementação vinculada. Mesmo um inventário de usuário aprovado não permite
que `--mode kernel` seja aprovado nesta versão de desenvolvimento.

Em 2026-09-30, uma consulta somente de leitura à referência upstream retornou
o master do Linux de Torvalds `551c722f40809618230001baccf219193e22fc5a`.
O [documento de licenciamento nesse commit](https://github.com/torvalds/linux/blob/551c722f40809618230001baccf219193e22fc5a/Documentation/process/license-rules.rst)
foi examinado. Trata-se de uma referência documental, não uma base selecionada
para integração, importação de fontes, teste do kernel nem proveniência do
snapshot herdado.

## Limites de formato e recursos

O commit fixado do codec para esta versão é
`e30dc9329be7cf9f233b1ac0b1fc9ed31f530391` (versão 2.65.13). Quando um commit
é registrado, o verificador exige esse HEAD Git exato e um inventário de
fontes/headers e LICENSE/NOTICE rastreado e sem modificações.

A configuração de teste fixa o modo FAST e o log da janela em 16, desativa
filtros BCJ, usa o build escalar do codec e trata cada página como um frame
independente do codec atual. O contexto do codificador, armazenado pelo
chamador, suporta no máximo 65.536 bytes de entrada, exige o alinhamento e
o tamanho de workspace consultados e é exclusivo de uma chamada por vez.
Sua reinicialização é comparada com contextos novos e chamadas únicas novas.
A saída precisa fornecer o limite de compressão do codec; a capacidade de
decodificação é verificada contra o tamanho esperado da página, em vez de
confiar no tamanho declarado pelo frame.

Este repositório não define um contêiner estável de páginas em disco nem um
formato para o kernel. Não promete interoperabilidade com o codec embutido
antigo 2.65.11, decodificadores mais antigos, builds com outra ordem de bytes
ou outras arquiteturas. Os testes atuais cobrem apenas o checkout vinculado
e a configuração de compilador do host. Os checksums detectam a corrupção
exercitada; desativá-los permite corrupção de payload sem detecção, portanto
essa configuração serve aqui somente para comparação de conformidade.
Os testes não exercitam falhas de alocação, concorrência, todos os streams
malformados, recuperação de memória pelo kernel, contexto atômico nem um
backend de dispositivo.

## Requisitos antes de qualquer trabalho futuro no kernel

Resolva uma concessão escrita de implementação compatível e conclua a revisão
de proveniência/licenças das dependências antes de importar código de
implementação. Selecione um commit upstream verificado, registre a URL da
fonte e o hash e projete a interface de compressão alvo contra essa fonte.
Defina o comportamento de alocação e bloqueio, limite o workspace e a pilha
para cada tamanho de página, defina o tratamento de dados incompressíveis,
erros e qualquer formato durável e teste em builds isolados do kernel e
máquinas virtuais. Builds do kernel, KUnit, zram/zswap, boot, stress de
recuperação de memória e envio upstream **NÃO FORAM EXECUTADOS** por este
pacote. Não se alega prontidão para produção no kernel nem aceitação upstream.

## Build estático opcional em espaço de usuário

O build local comum com GCC do Guix usa um interpretador no store do Guix e
não deve ser copiado para uma distribuição convencional como executável
portável. Um build opcional com musl pode usar um `musl-gcc` existente ou um
shell temporário do Guix, sem instalá-lo no perfil do usuário:

```sh
guix shell musl make -- make -j2 test CC=musl-gcc BUILD=build-musl \
  LDFLAGS='-static -Wl,-Map,build-musl/link.map -Wl,-t' \
  CODEC_DIR=/caminho/absoluto/para/vaptvupt-codec
readelf -l build-musl/page_conformance
readelf -d build-musl/page_conformance
```

O pacote Guix observado aqui é musl 1.2.6, proveniente de
`https://www.musl-libc.org/releases/musl-1.2.6.tar.gz`, com SHA-256 base32
do Guix `0ajic0jgiyfk2sk3brn1wsshq0kp9za8x7i4qcgiariwc4xzv1fm` e o patch
`musl-CVE-2026-40200.patch` do pacote. O texto COPYRIGHT completo instalado
está preservado em [LICENSES/musl.txt](../LICENSES/musl.txt). Inclua esse
aviso e os arquivos LICENSE/NOTICE do codec externo com binários estáticos
redistribuídos. Mantenha o mapa de vinculação e o registro do compilador/linker
ao selecionar um binário; uma libc estática, sozinha, não demonstra quais
objetos de runtime foram incluídos. Os resultados reais de testes e a
arquitetura precisam acompanhar cada build selecionado.

A vinculação observada com GCC 14.3.0 inclui `crtbeginS.o` e `crtendS.o` do
runtime do GCC. Seus termos GPL-3.0-or-later e a Exceção da Biblioteca de
Runtime do GCC 3.1 estão preservados em LICENSES; a exceção permite que uma
compilação elegível com GCC combine o runtime coberto com módulos
independentes sob seus próprios termos compatíveis. O mapa observado não
seleciona membros dos arquivos `libgcc.a`/`libgcc_eh.a` nem objetos do runtime
glibc. Estes comandos de build não usam plugins externos do compilador nem
transformações de representações intermediárias. Consulte a
[exceção de runtime do GCC](https://gcc.gnu.org/onlinedocs/libstdc++/manual/license.html).
