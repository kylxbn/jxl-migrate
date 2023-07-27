import 'dart:io';

import 'package:desktop_drop/desktop_drop.dart';
import 'package:flutter/material.dart';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/scheduler.dart';
import 'package:jxlmigrate/tools/tools.dart';
import 'package:path/path.dart';

import 'package:jxlmigrate/models/image_file.dart';
import 'package:jxlmigrate/models/menu_entry.dart';
import 'package:jxlmigrate/widgets/file_list.dart';
import 'package:jxlmigrate/models/convert_settings.dart';
import 'package:jxlmigrate/widgets/convert_settings_panel.dart';
import 'package:jxlmigrate/widgets/results_log.dart';
import 'package:shared_preferences/shared_preferences.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<ImageFile> _files = [];

  bool _filesLoading = false;
  bool _converting = false;
  bool _hovering = false;

  late final SharedPreferences _prefs;

  final Map<ConvertSettings, dynamic> _convertSettings = {
    ConvertSettings.lossyJpeg: false,
  };

  final List<String> _log = [];

  bool _requiredAppsExist = true;

  @override
  void initState() {
    super.initState();

    SharedPreferences.getInstance().then((instance) {
      _prefs = instance;
      setState(() {
        _convertSettings[ConvertSettings.lossyJpeg] =
            _prefs.getBool('prefs.${ConvertSettings.lossyJpeg.name}') ?? false;
      });
    });

    try {
      final ProcessResult res = Process.runSync('cjxl', ['-v']);
      if (res.exitCode != 0) {
        _requiredAppsExist = false;
      }
    } catch (e) {
      _requiredAppsExist = false;
    }

    if (!_requiredAppsExist) {
      SchedulerBinding.instance.addPostFrameCallback((_) {
        showDialog<void>(
          context: this.context,
          barrierDismissible: false,
          builder: (BuildContext context) {
            return AlertDialog(
              title: const Text('Missing Requirements'),
              content:
                  const Text('Make sure that the cjxl binary is in your PATH.'),
              actions: <Widget>[
                TextButton(
                  child: const Text('OK'),
                  onPressed: () {
                    Navigator.of(context).pop();
                  },
                ),
              ],
            );
          },
        );
      });
    }
  }

  List<MenuEntry> _getMenuItems() {
    return <MenuEntry>[
      MenuEntry(
        label: 'File',
        menuChildren: <MenuEntry>[
          MenuEntry(
            label: 'Add files to convert...',
            onPressed: (_filesLoading || _converting) ? null : _addFiles,
          ),
          MenuEntry(
            label: 'Start conversion',
            onPressed: (_files.isEmpty ||
                    (!_requiredAppsExist) ||
                    _filesLoading ||
                    _converting)
                ? null
                : _startConvert,
          ),
          MenuEntry(
            label: 'Clear files',
            onPressed: _files.isEmpty || _filesLoading || _converting
                ? null
                : () {
                    setState(() {
                      _files = [];
                    });
                  },
          ),
          MenuEntry(
            label: 'About',
            onPressed: () {
              showAboutDialog(
                context: this.context,
                applicationName: 'jxl-migrate',
                applicationVersion: 'v0.3.1',
                applicationIcon:
                    Image.asset('assets/icons/icon.png', width: 128),
                applicationLegalese: '© 2023 KYLXBN',
              );
            },
          ),
        ],
      ),
    ];
  }

  void _addFiles() async {
    final String? directoryPath = await getDirectoryPath();
    if (directoryPath != null) {
      setState(() {
        _filesLoading = true;
      });
      final dir = Directory(directoryPath);
      final List<FileSystemEntity> entities =
          await dir.list(recursive: true).toList();
      final foundFiles = entities.whereType<File>().toList();
      _actuallyAddFiles(foundFiles);
      setState(() {
        _filesLoading = false;
      });
    }
  }

  void _addFilesFromDrop(DropDoneDetails details) async {
    setState(() {
      _filesLoading = true;
    });
    for (XFile xf in details.files) {
      File? file = File(xf.path);
      while (file != null) {
        print(file.path);
        final FileStat fileStat = await file.stat();
        if (fileStat.type == FileSystemEntityType.directory) {
          // is directory
          final dir = Directory(file.path);
          final List<FileSystemEntity> entities =
            await dir.list(recursive: true).toList();
          final foundFiles = entities.whereType<File>().toList();
          _actuallyAddFiles(foundFiles);
        } else if (fileStat.type == FileSystemEntityType.file) {
          // is file
          _actuallyAddFiles([file]);
        } else if (fileStat.type == FileSystemEntityType.link) {
          // is link
          file = File(await file.resolveSymbolicLinks());
          continue;
        }
        file = null;
      }
    }
    setState(() {
      _filesLoading = false;
    });
  }

  void _actuallyAddFiles(List<File> files) {
    final imageFiles = files.where(filenameExtensionIsImage).map((f) {
      final String extension =
          getFileExtension(f) == 'jpg' ? 'jpeg' : getFileExtension(f);
      return ImageFile(
        name: basename(f.path),
        path: f.path,
        jpeg: extension == 'jpeg',
        lossless: isImageLossless(f),
      );
    }).toList();
    setState(() {
      _files.addAll(imageFiles);
    });
  }

  void _changeSettings(ConvertSettings which, bool val) async {
    if (which == ConvertSettings.lossyJpeg) {
      await _prefs.setBool('prefs.${which.name}', val);
    }
    setState(() {
      _convertSettings[which] = val;
    });
  }

  void _addLog(String l, {void Function()? extra}) {
    setState(() {
      _log.add(l);
      if (extra != null) {
        extra();
      }
    });
  }

  void _startConvert() async {
    final filesToProcess = [..._files];
    setState(() {
      _log.clear();
      _converting = true;
    });

    for (final imageFile in filesToProcess) {
      _addLog('Converting ${imageFile.name}...');

      ProcessResult result = await doConvert(imageFile, _convertSettings);

      if (result.exitCode != 0) {
        _addLog('    Conversion failed (code ${result.exitCode})');
      } else {
        _addLog('    Conversion OK', extra: () {
          _files.removeAt(0);
        });
      }
    }

    _addLog('Done.', extra: () {
      _converting = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Expanded(
                child: MenuBar(
                  children: MenuEntry.build(_getMenuItems()),
                ),
              ),
            ],
          ),
          Expanded(
            child: Row(
              children: [
                Expanded(
                  child: Container(
                    decoration: const BoxDecoration(
                      border: Border(
                        right: BorderSide(color: Colors.black45),
                      ),
                    ),
                    child: DropTarget(
                      onDragDone: _addFilesFromDrop,
                      onDragEntered: (details) {
                        setState(() {
                          _hovering = true;
                        });
                      },
                      onDragExited: (details) {
                        setState(() {
                          _hovering = false;
                        });
                      },
                      child: FileList(
                        files: _files,
                        loading: _filesLoading,
                        hovering: _hovering,
                      ),
                    ),
                  ),
                ),
                Expanded(
                  child: Container(
                    decoration: const BoxDecoration(
                      border: Border(
                        right: BorderSide(color: Colors.black45),
                      ),
                    ),
                    child: ConvertSettingsPanel(
                      settings: _convertSettings,
                      onSettingsChange: _changeSettings,
                    ),
                  ),
                ),
                Expanded(
                  child: ResultsLog(log: _log),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
