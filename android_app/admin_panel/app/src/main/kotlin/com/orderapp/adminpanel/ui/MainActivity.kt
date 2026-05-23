package com.orderapp.adminpanel.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ListAlt
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.orderapp.adminpanel.AdminPanelApp
import com.orderapp.adminpanel.ui.screens.*
import com.orderapp.adminpanel.ui.theme.AdminPanelTheme
import com.orderapp.adminpanel.util.PhoneFormatter
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private lateinit var viewModel: AdminViewModel

    private var pendingPhoneNumber: String? = null
    private val callPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            pendingPhoneNumber?.let { makeCall(it) }
        }
        pendingPhoneNumber = null
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        lifecycleScope.launch {
            val isConfigured = AdminPanelApp.get().container.prefs.isConfigured.first()
            initMainScreen(showSettings = !isConfigured)
        }
    }

    private fun initMainScreen(showSettings: Boolean) {
        viewModel = ViewModelProvider(this)[AdminViewModel::class.java]

        setContent {
            AdminPanelTheme {
                val navController = rememberNavController()
                val navBackStackEntry by navController.currentBackStackEntryAsState()
                val currentRoute = navBackStackEntry?.destination?.route ?: "orders"

                Scaffold(
                    bottomBar = {
                        NavigationBar {
                            NavigationBarItem(
                                icon = { Icon(Icons.Default.ListAlt, contentDescription = null) },
                                label = { Text("Siparişler") },
                                selected = currentRoute == "orders",
                                onClick = {
                                    if (currentRoute != "orders") {
                                        navController.navigate("orders") {
                                            popUpTo("orders") { inclusive = true }
                                        }
                                    }
                                }
                            )
                            NavigationBarItem(
                                icon = { Icon(Icons.Default.Phone, contentDescription = null) },
                                label = { Text("Aramalar") },
                                selected = currentRoute == "calls",
                                onClick = {
                                    if (currentRoute != "calls") {
                                        navController.navigate("calls") {
                                            popUpTo("orders")
                                        }
                                    }
                                }
                            )
                            NavigationBarItem(
                                icon = { Icon(Icons.Default.Add, contentDescription = null) },
                                label = { Text("Yeni Sipariş") },
                                selected = currentRoute == "order_edit",
                                onClick = {
                                    navController.navigate("order_edit") {
                                        popUpTo("orders")
                                    }
                                }
                            )
                            NavigationBarItem(
                                icon = { Icon(Icons.Default.Settings, contentDescription = null) },
                                label = { Text("Ayarlar") },
                                selected = currentRoute == "settings",
                                onClick = {
                                    if (currentRoute != "settings") {
                                        navController.navigate("settings") {
                                            popUpTo("orders")
                                        }
                                    }
                                }
                            )
                        }
                    }
                ) { innerPadding ->
                    NavHost(
                        navController = navController,
                        startDestination = if (showSettings) "settings" else "orders",
                        modifier = Modifier.padding(innerPadding)
                    ) {
                        composable("orders") {
                            OrdersScreen(
                                viewModel = viewModel,
                                onEditOrder = { orderId ->
                                    navController.navigate("order_edit/$orderId")
                                },
                                onCallPhone = { phone -> requestCallPermission(phone) }
                            )
                        }

                        composable("calls") {
                            CallsScreen(
                                viewModel = viewModel,
                                onCreateOrder = { customerId ->
                                    navController.navigate("order_edit?customerId=$customerId")
                                },
                                onCallPhone = { phone -> requestCallPermission(phone) }
                            )
                        }

                        composable("order_edit") {
                            OrderEditScreen(
                                viewModel = viewModel,
                                orderId = null,
                                preselectedCustomerId = null,
                                onDone = { navController.popBackStack() }
                            )
                        }

                        composable(
                            route = "order_edit/{orderId}",
                            arguments = listOf(navArgument("orderId") { type = NavType.StringType })
                        ) { backStackEntry ->
                            val orderId = backStackEntry.arguments?.getString("orderId")
                            OrderEditScreen(
                                viewModel = viewModel,
                                orderId = orderId,
                                preselectedCustomerId = null,
                                onDone = { navController.popBackStack() }
                            )
                        }

                        composable(
                            route = "order_edit?customerId={customerId}",
                            arguments = listOf(navArgument("customerId") {
                                type = NavType.StringType
                                defaultValue = ""
                            })
                        ) { backStackEntry ->
                            val customerId = backStackEntry.arguments?.getString("customerId")
                                ?.takeIf { it.isNotBlank() }
                            OrderEditScreen(
                                viewModel = viewModel,
                                orderId = null,
                                preselectedCustomerId = customerId,
                                onDone = { navController.popBackStack() }
                            )
                        }

                        composable("settings") {
                            SettingsScreen(
                                onConnectionSaved = {
                                    viewModel.loadReferenceData()
                                    viewModel.loadOrders()
                                    navController.navigate("orders") {
                                        popUpTo("settings") { inclusive = true }
                                    }
                                }
                            )
                        }
                    }
                }
            }
        }
    }

    private fun requestCallPermission(phone: String) {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CALL_PHONE)
            == PackageManager.PERMISSION_GRANTED
        ) {
            makeCall(phone)
        } else {
            pendingPhoneNumber = phone
            callPermissionLauncher.launch(Manifest.permission.CALL_PHONE)
        }
    }

    private fun makeCall(phone: String) {
        val dialable = PhoneFormatter.toDialable(phone)
        try {
            startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:$dialable")))
        } catch (e: Exception) {
            Toast.makeText(this, "Arama uygulaması açılamadı", Toast.LENGTH_SHORT).show()
        }
    }
}
