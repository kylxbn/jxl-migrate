class ImageFile {
  const ImageFile({
    required this.path,
    required this.name,
    required this.jpeg,
    required this.lossless,
  });

  final String path;
  final String name;
  final bool jpeg;
  final bool lossless;
}