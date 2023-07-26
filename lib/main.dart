import 'package:flutter/material.dart';

import 'package:jxlmigrate/screens/home.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'JPEG XL Migrate',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color.fromARGB(255, 59, 182, 179)),
        brightness: Brightness.light,
        useMaterial3: true,
      ),
      themeMode: ThemeMode.light,
      home: const HomeScreen(),
    );
  }
}
