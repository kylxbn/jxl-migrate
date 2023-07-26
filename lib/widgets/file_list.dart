import 'package:flutter/material.dart';

import 'package:jxlmigrate/models/image_file.dart';

class FileList extends StatelessWidget {
  const FileList({super.key, required this.files, required this.loading});

  final List<ImageFile> files;
  final bool loading;

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
              'Images',
              style: Theme.of(context).textTheme.titleLarge,
              textAlign: TextAlign.left,
            ),
          ),
        ),
        if (loading)
          const LinearProgressIndicator(
            value: null,
          ),
        if (files.isNotEmpty)
          Expanded(
            child: ListView.builder(
              itemCount: files.length,
              itemBuilder: (ctx, i) {
                return Container(
                  padding: const EdgeInsets.symmetric(
                    vertical: 8,
                    horizontal: 16,
                  ),
                  decoration: i > 0
                      ? const BoxDecoration(
                          border: Border(
                            top: BorderSide(color: Colors.black38),
                          ),
                        )
                      : null,
                  child: Text(
                    files[i].name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                );
              },
            ),
          )
        else
          const Expanded(
            child: Center(
              child: Padding(
                padding: EdgeInsets.all(8),
                child: Text('Please add files using the Files menu.'),
              ),
            ),
          )
      ],
    );
  }
}
