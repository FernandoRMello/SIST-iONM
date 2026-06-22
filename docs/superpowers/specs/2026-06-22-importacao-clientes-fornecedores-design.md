# Importação de Clientes e Fornecedores por Excel

## Objetivo

Permitir que usuários autorizados importem clientes e fornecedores por planilha `.xlsx`, com modelo oficial para download, atualização por CNPJ/CPF e resultado auditável na própria tela de cadastro.

## Escopo

- Disponível somente em `/cadastros/clients` e `/cadastros/suppliers`.
- Clientes: qualquer usuário autenticado, seguindo a permissão atual de cadastro.
- Fornecedores: somente administrador, seguindo a permissão atual de gravação.
- Nenhum outro CRUD recebe importação.

## Interface

Cada tela terá dois controles no cabeçalho:

1. `Baixar modelo Excel` — baixa arquivo `.xlsx` com aba `Importação`, cabeçalhos em português e aba `Instruções`.
2. `Importar planilha` — abre uma área compacta para selecionar um único `.xlsx` e enviar.

Após o processamento, um feedback informa quantos registros foram criados, atualizados e ignorados, além de até dez erros de linha.

## Formato e regras

- Limite: 5 MiB e 5.000 linhas de dados.
- Cabeçalhos devem corresponder exatamente ao modelo; ordem pode variar.
- `Nome` e `CNPJ/CPF`/`CNPJ` são obrigatórios.
- Documento é normalizado para comparação, removendo pontuação e diferenças de caixa.
- Documento existente atualiza o registro; documento novo cria registro.
- Documento repetido dentro da mesma planilha é ignorado e relatado.
- Linhas totalmente vazias são ignoradas.
- Arquivo inválido, aba ausente ou cabeçalho estrutural inválido aborta antes de qualquer escrita.
- Escritas válidas são executadas em uma única transação; erro de banco causa rollback integral.

## Arquitetura

`app/features/catalog_import/service.py` concentra geração, leitura, validação e persistência, sem depender de FastAPI. `app/main.py` apenas aplica autenticação/autorização, lê o upload, chama o serviço e grava feedback curto na sessão. `crud.html` exibe os controles condicionalmente e usa o design system existente.

## Endpoints

- `GET /cadastros/{table}/import-template`
- `POST /cadastros/{table}/import`

Ambos rejeitam tabelas fora de `clients` e `suppliers` com 404. O POST redireciona para `/cadastros/{table}` após armazenar feedback na sessão.

## Testes

- Modelos abrem com openpyxl e possuem cabeçalhos/instruções corretos.
- Cliente novo é criado e cliente existente é atualizado pelo documento.
- Fornecedor é importado por admin e rejeitado para vendedor.
- Arquivo inválido/cabeçalho incorreto não altera o banco.
- Botões aparecem somente nas duas telas autorizadas.
