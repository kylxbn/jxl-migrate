import 'dart:io';

import 'package:jxlmigrate/models/convert_settings.dart';
import 'package:jxlmigrate/models/image_file.dart';

const _supportedImageExtensions = [
  'jpg',
  'jpeg',
  'png',
];

String replaceExtension(String filename, String newExtension) {
  final dotIndex = filename.lastIndexOf('.');
  if (dotIndex < 0) {
    throw Exception('Filename does not have extension: $filename');
  }

  final filenameWithoutExtension = filename.substring(0, dotIndex);
  return '$filenameWithoutExtension.$newExtension';
}

String getFileExtension(File f) {
  final dotIndex = f.path.lastIndexOf('.');
  if (dotIndex < 0) {
    throw Exception('File does not have extension: ${f.path}');
  }

  return f.path.substring(dotIndex + 1).toLowerCase();
}

bool filenameExtensionIsImage(File f) {
  return _supportedImageExtensions.contains(getFileExtension(f));
}

bool isImageLossless(File file) {
  final extension = getFileExtension(file);
  return extension == 'png';

  // TODO: WebP can be lossy or lossless, so we gotta check.
}

Future<ProcessResult> doConvert(
    ImageFile imageFile, Map<ConvertSettings, dynamic> convertSettings) async {
  final String sourcePath = imageFile.path;
  final String outPath = replaceExtension(sourcePath, 'jxl');

  final List<String> distance =
      (imageFile.jpeg && (convertSettings[ConvertSettings.lossyJpeg] as bool))
          ? ['-d', '1']
          : ['-d', '0'];
  
  final List<String> losslessJpeg =
      (imageFile.jpeg && (convertSettings[ConvertSettings.lossyJpeg] as bool))
          ? ['-j', '0']
          : ['-j', '1'];

  final List<String> arguments = [
    sourcePath,
    outPath,
    ...losslessJpeg,
    ...distance,
  ];

  final ProcessResult result = await Process.run('cjxl', arguments);

  if (result.exitCode == 0) {
    final File inFile = File(sourcePath);
    final File outFile = File(outPath);
    outFile.setLastModifiedSync(inFile.lastModifiedSync());
    inFile.deleteSync();
  }

  return result;
}
