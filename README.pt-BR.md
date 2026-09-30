<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Cristian Cezar Moisés. -->
# Pacote de desenvolvimento VaptVupt Linux

[English](README.md)

Versão **0.1.0-dev.1**. Este repositório pequeno fornece um teste C de
conformidade de páginas em espaço de usuário e um verificador delimitado de
proveniência/licenças para avaliar um checkout canônico externo do VaptVupt
Codec **2.65.13**. Não contém fonte do Linux, cópia do codec, módulo do kernel,
backend zram/zswap nem ABI do kernel.

A integração ao kernel está **BLOQUEADA**. A licença Apache-2.0 do codec atual
e destas ferramentas não concede uma implementação para o kernel
GPL-2.0-only. O aviso BSD-2-Clause do XXH64 do codec continua aplicável.
Não se presume uma concessão a partir de um rótulo de módulo ou de testes
aprovados em espaço de usuário. Consulte as [notas de desenvolvimento](docs/development.pt-BR.md)
e a [proveniência](PROVENANCE.json).

## Executar as verificações em espaço de usuário

Pré-requisitos: GNU Make, GCC ou Clang com compilador/linker C11, Python 3.9+
e o checkout externo do codec. Não é necessário acesso root nem alterar o
kernel. Mantenha os arquivos LICENSE e NOTICE da dependência com qualquer
binário vinculado que seja redistribuído.

```sh
make -j2 test CODEC_DIR=/caminho/absoluto/para/vaptvupt-codec
make -j2 test CC=clang BUILD=build-clang CODEC_DIR=/caminho/absoluto/para/vaptvupt-codec
make -j2 test CC=clang BUILD=build-sanitize \
  CFLAGS='-O1 -g -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined' CODEC_DIR=/caminho/absoluto/para/vaptvupt-codec
python3 scripts/check_provenance.py --codec /caminho/absoluto/para/vaptvupt-codec --mode kernel
```

O último comando retorna **2** intencionalmente e imprime `BLOCKED`. Um erro
de metadados ou de inventário de licenças retorna **1** com `FAIL`; uma
verificação do escopo de usuário retorna **0** com `PASS`. `make kernel-gate`
expõe a mesma verificação bloqueada; o próprio GNU Make retorna 2 quando uma
receita falha. Diretórios de build separados evitam misturar objetos
compilados com compiladores ou opções de sanitização diferentes.

O teste verifica páginas de 4, 16 e 64 KiB com cinco fixtures determinísticos,
com checksum desligado e ligado: 30 casos. Verifica o comprimento decodificado
exato, igualdade de bytes, reinicialização independente do dicionário e do
histórico, equivalência entre contextos novos e reutilizados, capacidades de
compressão/descompressão, frames malformados/truncados e sentinelas ao redor
da entrada, da saída e do armazenamento de contexto do chamador. Usa a
compilação escalar do codec externo real, não um algoritmo substituto.
São testes finitos de conformidade, não resultados de desempenho nem prova
de segurança.

## Arquivos de release

Os novos arquivos de release usam o contêiner Zupt `.zupt`, não um frame
bruto do codec. Use a CLI Zupt instalada separadamente para listar, testar
e extrair em um diretório novo; este pacote não é um módulo do kernel:

```sh
zupt list vaptvuptlinux-0.1.0-dev.1-source.zupt
zupt test vaptvuptlinux-0.1.0-dev.1-source.zupt
zupt extract vaptvuptlinux-0.1.0-dev.1-source.zupt -o ./vaptvuptlinux-source
```

Verifique primeiro os checksums da release e sua assinatura OpenPGP
destacada. Os arquivos de fontes e executáveis são separados; cada binário
se limita à arquitetura e à validação informadas nas notas da release.

Licença: [Apache-2.0](LICENSE). Copyright 2026 Cristian Cezar Moisés.
