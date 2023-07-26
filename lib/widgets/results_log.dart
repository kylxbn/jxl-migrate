import 'package:flutter/material.dart';

class ResultsLog extends StatelessWidget {
  const ResultsLog({
    super.key,
    required this.log,
  });

  final List<String> log;

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
              'Output Log',
              style: Theme.of(context).textTheme.titleLarge,
              textAlign: TextAlign.left,
            ),
          ),
        ),
        Expanded(
          child: log.isNotEmpty
              ? ListView.builder(
                  itemCount: log.length,
                  itemBuilder: (ctx, i) {
                    return Padding(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
                        child: Text(log[i]));
                  },
                )
              : const Center(child: Text('No logs yet.')),
        ),
      ],
    );
  }
}
