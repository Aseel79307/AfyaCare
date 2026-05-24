import 'package:flutter/material.dart';

class Medication {
  final String id;
  final String name;
  final String dosage;
  final String frequency;
  final TimeOfDay time;
  final bool isTaken;
  final String? userId;

  Medication({
    required this.id,
    required this.name,
    required this.time,
    this.dosage = '',
    this.frequency = 'daily',
    this.isTaken = false,
    this.userId,

  });

  String get formattedTime =>
      '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';

  Medication copyWith({
    String? id,
    String? name,
    String? dosage,
    String? frequency,
    TimeOfDay? time,
    bool? isTaken,
    String? userId,
    }) {
     return Medication(
      id: id ?? this.id,
      name: name ?? this.name,
      dosage: dosage ?? this.dosage,
      frequency: frequency ?? this.frequency,
      time: time ?? this.time,
      isTaken: isTaken ?? this.isTaken,
      userId: userId ?? this.userId,
    );
  }
  // Convert to JSON for API
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'dosage': dosage,
      'frequency': frequency,
      'time': formattedTime,
      'is_taken': isTaken,
      'user_id': userId,
    };
  }
  // Create from JSON from API
  factory Medication.fromJson(Map<String, dynamic> json) {
  String timeStr = json['time'] ?? '08:00';
  
  int hour = 8;
  int minute = 0;
  
  // Extract just the numbers from the time string
    final RegExp numRegex = RegExp(r'\d+');
    final Iterable<Match> matches = numRegex.allMatches(timeStr);
    final List<int> numbers = matches.map((m) => int.parse(m.group(0)!)).toList();
    
    if (numbers.isNotEmpty) {
      hour = numbers[0];
      if (numbers.length > 1) {
        minute = numbers[1];
      }
    }
    
    // If it's PM (contains 'م') and hour is less than 12, add 12
    if (timeStr.contains('م') && hour < 12) {
      hour += 12;
    }
    
    // If hour is 24, make it 0
    if (hour == 24) {
      hour = 0;
    }
    
    return Medication(
      id: json['id'].toString(),
      name: json['name'],
      dosage: json['dosage'] ?? '',
      frequency: json['frequency'] ?? 'daily',
      time: TimeOfDay(hour: hour, minute: minute),
      isTaken: json['is_taken'] ?? false,
      userId: json['user_id'],
    );
  }
}
