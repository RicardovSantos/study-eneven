# Convenções deste repositório

## Autoria dos commits

Todo commit criado neste repositório deve usar sempre o nome e o e-mail do
dono do projeto, nunca "Claude" ou o e-mail padrão do harness:

```
git -c user.name="Ricardo Santos" -c user.email="ricardovieirads@outlook.com" commit ...
```

Isso vale tanto para `author` quanto para `committer`. Se um commit for
criado por engano com outra identidade, reescreva-o com
`git commit --amend --reset-author` (ou rebase, se não for o topo do
branch) antes de enviar para o remoto.

O e-mail `ricardovieirads@outlook.com` é o mesmo cadastrado no perfil do
GitHub do usuário (`RicardovSantos`) — é ele que faz o commit aparecer
vinculado à conta, com foto e link de perfil.
