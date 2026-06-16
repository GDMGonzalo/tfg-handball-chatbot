# Contribución

## Configuración de GitHub (primer uso)

### Acceso al repositorio
1) Acepta la invitación al repo desde GitHub.
2) Clona el repositorio:
```bash
git clone https://github.com/rmluqueuma/handballAnalytics.git
cd handballAnalytics
```

### Autenticación (HTTPS)
GitHub no permite contraseña en `git push`. Usa un **token**:
1) GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic).
2) Crea un token con scope `repo`.
3) En el primer `git push`, usa el token como “password”.

### Crear tu rama (una sola rama por TFG)
```bash
git checkout -b tfg-nombre-apellidos
git push -u origin tfg-nombre-apellidos
```

### Cuándo abrir Pull Request (PR)
- **Al finalizar la funcionalidad completa** del TFG, abre un PR a `main`.
- Si el desarrollo se organiza por bloques, abre PRs **al completar cada bloque acordado** para que el profesor los revise y mergee.

### Reglas
- No se permite `push` directo a `main`.
- El merge a `main` lo hace el profesor tras revisar.

### Actualizar tu rama con `main`
Esto sirve para **traer a tu rama los cambios nuevos del profesor o de otros merges**, evitando conflictos grandes al final. Solo hay que realizarlo cuando se avise.

```bash
git fetch origin
git checkout tfg-nombre-apellidos
git merge origin/main
```
