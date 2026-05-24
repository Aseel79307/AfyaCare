import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class AuthService {
  static const String baseUrl = 'http://10.0.2.2:8000'; // Android emulator
  
  Future<Map<String, dynamic>> signUp({
    required String email,
    required String password,
    required String name,
    int? age,
    String? gender,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/signup'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
        'name': name,
        'age': age,
        'gender': gender,
      }),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      // Save token
      if (data['access_token'] != null) {
        await _saveToken(data['access_token']);
        await _saveUser(data['user']);
      }
      return data;
    } else {
      throw Exception(jsonDecode(response.body)['detail'] ?? 'Signup failed');
    }
  }
  
  Future<Map<String, dynamic>> signIn({
    required String email,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/signin'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
      }),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data['access_token'] != null) {
        await _saveToken(data['access_token']);
        await _saveUser(data['user']);
      }
      return data;
    } else {
      throw Exception(jsonDecode(response.body)['detail'] ?? 'Login failed');
    }
  }
  
  Future<void> signOut() async {
    final token = await getToken();
    if (token != null) {
      await http.post(
        Uri.parse('$baseUrl/auth/signout'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'access_token': token}),
      );
    }
    await _clearStorage();
  }
  
  Future<void> _saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', token);
  }
  
  Future<void> _saveUser(Map<String, dynamic> user) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('user', jsonEncode(user));
  }
  
  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }
  
  Future<Map<String, dynamic>?> getCurrentUser() async {
    final prefs = await SharedPreferences.getInstance();
    final userString = prefs.getString('user');
    if (userString != null) {
      return jsonDecode(userString);
    }
    return null;
  }
  
  Future<void> _clearStorage() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('user');
  }
  
  Future<bool> isLoggedIn() async {
    final token = await getToken();
    return token != null;
  }

  // Forgot password - sends reset email
Future<bool> resetPassword(String email) async {
  try {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/forgot-password'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email}),
    );
    return response.statusCode == 200;
  } catch (e) {
    print('Error sending reset email: $e');
    return false;
  }
}

// Update password with reset token
  Future<bool> updatePassword(String token, String newPassword) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/reset-password'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'token': token, 'new_password': newPassword}),
      );
      return response.statusCode == 200;
    } catch (e) {
      print('Error updating password: $e');
      return false;
    }
  }


   Future<bool> verifyOTP(String email, String token) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/verify-otp'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'token': token}),
      );
      return response.statusCode == 200;
    } catch (e) {
      print('Error verifying OTP: $e');
      return false;
    }
  }
}