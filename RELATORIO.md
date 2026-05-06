# Relatorio do Projeto - pixel_buddy

## 1. Identificacao

**Projeto:** pixel_buddy  
**Tipo:** Aplicacao web com agente de firewall  
**Backend:** Flask  
**Banco de dados:** SQLite com Flask-SQLAlchemy  
**Autenticacao:** Flask-Login  
**Interface:** HTML/Jinja, CSS e renderer de imagem com Pillow  
**Agente local:** Python, Scapy e UFW

## 2. Resumo do Projeto

O `pixel_buddy` e uma aplicacao web inspirada em bichinhos virtuais no estilo
Pwnagotchi, mas adaptada para um contexto educacional de seguranca.

A aplicacao funciona como um painel web onde o usuario cria uma conta, acessa seu
buddy virtual, cadastra agentes, acompanha eventos de rede e gerencia uma lista
de IPs bloqueados. O agente Python roda em uma maquina Linux protegida, monitora
trafego com Scapy, aplica regras de firewall com UFW e reporta eventos para a
aplicacao Flask.

O objetivo e demonstrar, de forma simples e visual, como uma plataforma web pode
interagir com um agente local de seguranca.

## 3. Prints da Aplicacao

### 3.1 Tela de Login

> Espaco reservado para print da tela de login.

---

### 3.2 Tela Principal do Buddy

> Espaco reservado para print da tela `/game`, mostrando o buddy renderizado.

---

### 3.3 Tela de Cadastro de Agente

> Espaco reservado para print da tela `/agents`, com criacao de token do agente.

---

### 3.4 Tela de Blocklist

> Espaco reservado para print da tela `/blocked-ips`, mostrando os IPs cadastrados.

---

### 3.5 Tela de Upload de PCAP

> Espaco reservado para print da tela `/pcaps/upload`.

---

### 3.6 Agente Rodando no Terminal

> Espaco reservado para print do agente Python em execucao na VM.

---

## 4. Funcionalidades Implementadas

### 4.1 Autenticacao de Usuarios

A aplicacao possui fluxo de autenticacao com:

- cadastro de usuario;
- login;
- logout;
- protecao de rotas com `login_required`;
- sessao mantida por cookie do Flask/Flask-Login.

As rotas principais ficam no blueprint `auth`, em `app/auth/routes.py`.

### 4.2 Buddy Virtual

Cada usuario possui um buddy virtual associado a sua conta. O buddy tem atributos
como:

- nome;
- energia;
- curiosidade;
- XP de rede;
- humor atual.

A tela do buddy e renderizada como imagem PNG usando Pillow, no arquivo
`app/display/renderer.py`. O visual segue uma estetica retro, em preto e branco,
parecida com telas simples de e-ink.

### 4.3 Tema por Cookie

A aplicacao possui tema claro/escuro controlado pelo cookie `pet_theme`.

Esse cookie guarda uma preferencia visual simples do usuario:

- `pet_theme=dark`;
- `pet_theme=light`.

O mesmo tema tambem afeta a imagem renderizada do buddy. Quando o tema esta em
modo escuro, o renderer inverte as cores da tela do pet.

### 4.4 Cadastro e Sincronizacao de Agentes

O usuario autenticado pode cadastrar um agente em `/agents`. Ao criar um agente,
a aplicacao gera um token que sera usado pelo script Python rodando na maquina
protegida.

O agente usa esse token para se comunicar com a API:

- enviar eventos detectados;
- buscar a lista de IPs ativos para bloqueio.

### 4.5 Blocklist de IPs

A Web UI permite cadastrar, editar, visualizar e remover IPs da blocklist.

O fluxo correto do sistema e:

1. O usuario cadastra um IP na Web UI.
2. O IP fica ativo no banco da aplicacao.
3. O agente consulta a API `/api/agent/blocked-ips`.
4. O agente aplica o bloqueio localmente.
5. Se o IP for removido da Web UI, o agente remove a regra local no proximo sync.

Em modo `ufw`, o agente executa comandos como:

```bash
ufw deny from <ip>
ufw delete deny from <ip>
```

Em modo `dry-run`, o agente apenas reporta o que faria, sem alterar o firewall.

### 4.6 Monitoramento de Rede com Scapy

O agente pode monitorar pacotes TCP usando Scapy. A deteccao e propositalmente
simples e didatica:

- observa pacotes destinados ao IP protegido;
- ignora portas administrativas configuradas, como SSH;
- conta pacotes por origem e porta;
- quando o limite e atingido, gera um evento `possible_dos`.

Se estiver em modo `ufw`, o agente pode bloquear automaticamente a origem
detectada.

### 4.7 Upload e Analise de PCAP

A aplicacao tambem possui uma tela para upload de arquivos `.pcap`, `.pcapng` e
`.cap`.

O arquivo e processado temporariamente, sem ser armazenado permanentemente. A
analise busca padroes simples de muitos pacotes em uma janela de tempo. Quando
detecta um evento suspeito, registra um `FirewallEvent` e atualiza o buddy.

### 4.8 Ranking

A aplicacao possui uma tela de ranking baseada no XP de rede do buddy. Usuarios
com maior `network_xp` aparecem primeiro.

## 5. Arquitetura Geral

### 5.1 Modulos Principais

| Modulo | Responsabilidade |
| --- | --- |
| `app/auth` | Cadastro, login, logout e modelo de usuario |
| `app/pets` | Modelo e logica de estado do buddy |
| `app/display` | Renderizacao da tela do buddy com Pillow |
| `app/firewall` | Agentes, eventos, blocklist, API e upload de PCAP |
| `agent` | Agente local com Scapy, TUI e integracao com UFW |
| `scripts` | Utilitarios para inspecionar o banco SQLite |

### 5.2 Modelos do Banco

Os principais modelos persistidos sao:

- `User`: conta autenticada do usuario;
- `Pet`: buddy virtual associado ao usuario;
- `Agent`: agente cadastrado e autenticado por token;
- `FirewallEvent`: eventos reportados pelo agente ou por analise de PCAP;
- `BlockedIP`: IPs da blocklist do usuario.

## 6. Fluxo de Uso

1. Usuario cria uma conta.
2. Usuario acessa `/game` e visualiza seu buddy.
3. Usuario cria um agente em `/agents`.
4. Usuario copia o token do agente.
5. Agente e configurado e executado na maquina protegida.
6. Usuario cadastra IPs na blocklist ou simula trafego suspeito.
7. Agente sincroniza a blocklist e aplica/remover regras locais.
8. Agente reporta eventos para a API.
9. Buddy muda humor/estado conforme os eventos recebidos.

## 7. Vulnerabilidade Demonstrada: IDOR

### 7.1 O que e IDOR

IDOR significa **Insecure Direct Object Reference**. Essa vulnerabilidade ocorre
quando uma aplicacao acessa um objeto diretamente pelo ID recebido na URL, sem
verificar se o usuario autenticado tem permissao para acessar aquele objeto.

No projeto, a demonstracao usa a entidade `BlockedIP`.

Exemplo de rota vulneravel:

```text
/blocked-ips/<blocked_ip_id>
```

Se a aplicacao buscar apenas pelo ID, um usuario pode alterar manualmente a URL e
tentar acessar um registro que pertence a outro usuario.

### 7.2 Codigo Vulneravel Usado na Demonstracao

No arquivo `app/firewall/routes.py`, a funcao abaixo foi deixada vulneravel de
proposito para a apresentacao:

```python
def get_owned_blocked_ip(blocked_ip_id):
    return BlockedIP.query.filter_by(id=blocked_ip_id).first_or_404()
```

O problema e que a consulta filtra apenas pelo `id` do registro. Ela nao valida
se o `BlockedIP` pertence ao usuario logado.

### 7.3 Como Demonstrar

Fluxo da demonstracao:

1. Criar/login com o usuario A.
2. Criar um registro de IP bloqueado.
3. Anotar o ID do registro na URL.
4. Fazer logout.
5. Criar/login com o usuario B.
6. Acessar manualmente `/blocked-ips/<id_do_usuario_A>`.
7. Mostrar que o usuario B consegue acessar um registro que nao e dele.

Esse comportamento demonstra a falha de controle de acesso.

### 7.4 Correcao da Vulnerabilidade

A correcao e incluir o `user_id` do usuario autenticado na consulta:

```python
def get_owned_blocked_ip(blocked_ip_id):
    return BlockedIP.query.filter_by(
        id=blocked_ip_id,
        user_id=current_user.id,
    ).first_or_404()
```

Com essa correcao, o registro so e encontrado se:

- o ID da URL existir;
- o registro pertencer ao usuario logado.

Caso outro usuario tente acessar o mesmo ID, a aplicacao retorna `404`.

### 7.5 Observacao Sobre a API do Agente

A API do agente nao usa a funcao vulneravel da Web UI. Ela autentica pelo token
do agente e busca os IPs ativos pelo `user_id` dono daquele agente:

```python
BlockedIP.query.filter_by(user_id=agent.user_id, active=True)
```

Assim, a vulnerabilidade fica isolada para a demonstracao nas rotas HTML da Web
UI, enquanto a API do agente continua usando controle de acesso correto.

## 8. Medidas de Seguranca Implementadas

Alem da demonstracao da IDOR, o projeto possui algumas protecoes:

- rotas autenticadas com Flask-Login;
- validacao CSRF em formularios POST;
- senhas armazenadas como hash;
- tokens de agente armazenados como hash;
- API do agente protegida por Bearer Token;
- validacao de IPs com `ipaddress`;
- limite de tamanho para upload de PCAP;
- cookie de tema sem informacao sensivel.

## 9. Conclusao

O `pixel_buddy` demonstra uma aplicacao Flask com autenticacao, banco de dados,
interface web, cookies, renderizacao visual, processamento de PCAP e integracao
com um agente local de firewall.

O projeto tambem apresenta uma vulnerabilidade IDOR de forma controlada para fins
didaticos, mostrando o problema e a correcao adequada com filtro por propriedade
do usuario.

O resultado final e uma plataforma simples, com aparencia retro, que conecta uma
Web UI estilo SaaS a um agente Python executado em uma maquina Linux protegida.
