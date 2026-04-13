/// Ejemplo Dart/Flutter mínimo para validar el pipeline multi-lenguaje.

String greet(String name) {
  return 'Hola, $name — bienvenido a Nexus-AI';
}

class NexusConfig {
  final String tenantId;

  const NexusConfig({required this.tenantId});
}
