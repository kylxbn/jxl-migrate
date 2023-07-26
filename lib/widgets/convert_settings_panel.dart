import 'package:flutter/material.dart';

import 'package:jxlmigrate/models/convert_settings.dart';

class ConvertSettingsPanel extends StatelessWidget {
  const ConvertSettingsPanel({super.key, required this.settings, required this.onSettingsChange});

  final Map<ConvertSettings, dynamic> settings;
  final void Function(ConvertSettings, bool) onSettingsChange;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Material(
          elevation: 4,
          child: Padding(
            padding: const EdgeInsets.symmetric(
              vertical: 8,
              horizontal: 16,
            ),
            child: Text(
              'Conversion Settings',
              style: Theme.of(context).textTheme.titleLarge,
              textAlign: TextAlign.left,
            ),
          ),
        ),
        Expanded(
          child: ListView(
            children: [
              CheckboxListTile(
                value: settings[ConvertSettings.lossyJpeg] as bool,
                onChanged: (val) {
                  if (val != null) {
                    onSettingsChange(ConvertSettings.lossyJpeg, val);
                  }
                },
                title: const Text('Force lossy JPEG conversion'),
              )
            ],
          ),
        )
      ],
    );
  }
}
