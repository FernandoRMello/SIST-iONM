# Perfil: enquadramento e recorte do avatar

Data: 22/06/2026

## Objetivo

Permitir selecionar, enquadrar, arrastar e aplicar zoom à foto dentro de uma moldura circular antes de salvá-la.

## Experiência

Selecionar uma imagem abre o editor na própria página. O editor contém:

- moldura circular de prévia;
- arraste por mouse ou toque;
- controle de zoom;
- botões `Cancelar` e `Salvar foto`;
- status acessível de processamento e erro.

A moldura circular representa o resultado exibido. O arquivo enviado será quadrado em 512 × 512 pixels para funcionar de forma consistente no chat, feed, perfil e organograma.

## Cliente

Criar `profile-avatar-editor.js`, sem dependência externa. O script usará `FileReader`, `Image`, Pointer Events e Canvas. A escala mínima sempre cobrirá a moldura. O deslocamento será limitado para impedir áreas vazias.

Ao salvar, o Canvas produzirá JPEG com qualidade 0,9 e enviará o blob no formulário atual. A navegação sem JavaScript continuará permitindo upload tradicional; o servidor fará o recorte central nesse fallback.

O inicializador responderá a `sistionm:content-updated`, pois o Perfil pode ser aberto pela navegação persistente do menu.

## Servidor

Pillow será declarada como dependência direta. O endpoint aceitará JPEG, PNG, WebP e GIF de até 10 MiB, validará o conteúdo decodificando a imagem, corrigirá orientação EXIF, converterá para RGB, recortará um quadrado central quando necessário e salvará JPEG 512 × 512 com nome físico aleatório.

Metadados serão removidos pela regravação. Arquivos inválidos não substituirão o avatar atual.

## Segurança e acessibilidade

- Não confiar em extensão nem `Content-Type` isoladamente.
- Limitar pixels decodificados para evitar imagens-bomba.
- Não usar SVG ou HTML.
- Editor operável com mouse, toque e controle de zoom por teclado.
- Botões e status possuem nomes acessíveis; foco retorna ao seletor ao cancelar.

## Testes

- Imagem paisagem e retrato resultam em JPEG 512 × 512.
- Orientação EXIF é corrigida.
- Arquivo corrompido, formato proibido e tamanho excessivo são rejeitados sem alterar perfil.
- Template contém moldura, zoom, cancelar e status acessível.
- Script é versionado, sem handlers inline e reinicializa após navegação parcial.
- Foto processada aparece no Perfil, Feed e Chat.

